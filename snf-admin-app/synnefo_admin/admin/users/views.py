# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
logger = logging.getLogger(__name__)
import re
from collections import OrderedDict

from operator import or_

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group

from synnefo.db.models import (VirtualMachine, Network, IPAddressLog, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import AstakosUser, ProjectMembership, Project, Resource
from astakos.im import user_logic as users

from astakos.api.quotas import get_quota_usage
from astakos.im.user_utils import send_plain as send_email

from synnefo.util import units

from eztables.views import DatatablesView

import django_filters
from django.db.models import Q

from synnefo_admin.admin.actions import (has_permission_or_403,
                                         get_allowed_actions,
                                         get_permitted_actions,)
from synnefo_admin.admin.utils import (get_actions, render_email,
                                       create_details_href)

from .utils import (get_user, get_quotas, get_user_groups,
                    get_enabled_providers, get_suspended_vms, )
from .actions import cached_actions
from .filters import UserFilterSet

SHOW_DELETED_VMS = getattr(settings, 'ADMIN_SHOW_DELETED_VMS', False)

templates = {
    'list': 'admin/user_list.html',
    'details': 'admin/user_details.html',
}


class UserJSONView(DatatablesView):
    model = AstakosUser
    fields = ('email', 'first_name', 'last_name', 'is_active',
              'is_rejected', 'moderated', 'email_verified')
    filters = UserFilterSet

    def get_extra_data(self, qs):
        if self.form.cleaned_data['iDisplayLength'] < 0:
            qs = qs.only('email', 'first_name', 'last_name', 'is_active',
                         'is_rejected', 'moderated', 'email_verified', 'uuid')
        return [self.get_extra_data_row(row) for row in qs]

    def get_extra_data_row(self, inst):
        if self.dt_data['iDisplayLength'] < 0:
            extra_dict = {}
        else:
            extra_dict = OrderedDict()

        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(cached_actions, inst,
                                         self.request.user),
            'visible': False,
        }
        extra_dict['id'] = {
            'display_name': "UUID",
            'value': inst.uuid,
            'visible': True,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': inst.realname,
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['user', inst.uuid]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': inst.uuid,
            'visible': False,
        }
        extra_dict['contact_email'] = {
            'display_name': "Contact email",
            'value': inst.email,
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': inst.realname,
            'visible': False,
        }

        if self.form.cleaned_data['iDisplayLength'] < 0:
            extra_dict['minimal'] = {
                'display_name': "No summary available",
                'value': "Have you per chance pressed 'Select All'?",
                'visible': True,
            }
        else:
            extra_dict.update(self.add_verbose_data(inst))

        return extra_dict

    def add_verbose_data(self, inst):
        extra_dict = OrderedDict()
        extra_dict['status'] = {
            'display_name': "Status",
            'value': inst.status_display,
            'visible': True,
        }
        extra_dict['groups'] = {
            'display_name': "Groups",
            'value': get_user_groups(inst),
            'visible': True,
        }
        extra_dict['enabled_providers'] = {
            'display_name': "Enabled providers",
            'value': get_enabled_providers(inst),
            'visible': True,
        }

        if users.validate_user_action(inst, "ACCEPT"):
            extra_dict['activation_url'] = {
                'display_name': "Activation URL",
                'value': inst.get_activation_url(),
                'visible': True,
            }

        if inst.accepted_policy:
            extra_dict['moderation_policy'] = {
                'display_name': "Moderation policy",
                'value': inst.accepted_policy,
                'visible': True,
            }

        suspended_vms = get_suspended_vms(inst)

        extra_dict['suspended_vms'] = {
            'display_name': "Suspended VMs",
            'value': suspended_vms,
            'visible': True,
        }

        return extra_dict


@has_permission_or_403(cached_actions)
def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    user = get_user(id)
    actions = get_permitted_actions(cached_actions, request.user)
    logging.info("Op: %s, target: %s, fun: %s", op, user.email, actions[op].f)

    if op == 'reject':
        actions[op].f(user, 'Rejected by the admin')
    elif op == 'contact':
        subject, body = render_email(request.POST, user)
        actions[op].f(user, subject, template_name=None, text=body)
    else:
        actions[op].f(user)


def catalog(request):
    """List view for Astakos users."""

    context = {}
    context['action_dict'] = get_permitted_actions(cached_actions, request.user)
    context['filter_dict'] = UserFilterSet().filters.itervalues()
    context['columns'] = ["E-mail", "First Name", "Last Name", "Active",
                          "Rejected", "Moderated", "Verified", ""]
    context['item_type'] = 'user'

    return context


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    user = get_user(query)
    quota_list = get_quotas(user)

    project_memberships = ProjectMembership.objects.filter(person=user)
    project_list = map(lambda p: p.project, project_memberships)

    vm_list = VirtualMachine.objects.filter(
        userid=user.uuid).order_by('deleted')

    volume_list = Volume.objects.filter(userid=user.uuid).order_by('deleted')

    filter_extra = {}
    show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    if not show_deleted:
        filter_extra['deleted'] = False

    public_networks = Network.objects.filter(
        public=True, nics__machine__userid=user.uuid,
        **filter_extra).order_by('state').distinct()
    private_networks = Network.objects.filter(
        userid=user.uuid, **filter_extra).order_by('state')
    network_list = list(public_networks) + list(private_networks)

    nic_list = NetworkInterface.objects.filter(userid=user.uuid)
    ip_list = IPAddress.objects.filter(userid=user.uuid).order_by('deleted')

    qor = [Q(server_id=vm.pk) for vm in vm_list]
    ip_log_list = []
    if qor:
        qor = reduce(or_, qor)
        ip_log_list = IPAddressLog.objects.filter(qor).order_by("allocated_at")

    for ipaddr in ip_log_list:
        ipaddr.ip = IPAddress.objects.get(address=ipaddr.address)
        ipaddr.vm = VirtualMachine.objects.get(id=ipaddr.server_id)
        ipaddr.network = Network.objects.get(id=ipaddr.network_id)
        ipaddr.user = user

    context = {
        'main_item': user,
        'main_type': 'user',
        'action_dict': get_permitted_actions(cached_actions, request.user),
        'associations_list': [
            (quota_list, 'quota', None),
            (project_list, 'project', get_actions("project", request.user)),
            (vm_list, 'vm', get_actions("vm", request.user)),
            (volume_list, 'volume', get_actions("volume", request.user)),
            (network_list, 'network', get_actions("network", request.user)),
            (nic_list, 'nic', None),
            (ip_list, 'ip', get_actions("ip", request.user)),
            (ip_log_list, 'ip_log', None),
        ]
    }

    return context


# DEPRECATED
#@csrf_exempt
#@admin_user_required
#def account_actions(request, op, account):
    #"""Entry-point for operation on an account."""
    #logging.info("Account action \"%s\" on %s started by %s",
                 #op, account, request.user_uniq)

    #if request.method == "POST":
        #logging.info("POST body: %s", request.POST)
    #redirect = reverse('admin-details', args=(account,))
    #user = get_user(account)
    #logging.info("I'm here!")

    ## Try to get mail body, if any.
    #try:
        #mail = request.POST['text']
    #except:
        #mail = None

    #try:
        #account_actions__(op, user, extra={'mail': mail})
    #except AdminActionNotPermitted:
        #logging.info("Account action \"%s\" on %s is not permitted",
                     #op, account)
        #redirect = "%s?error=%s" % (redirect, "Action is not permitted")
    #except AdminActionUnknown:
        #logging.info("Unknown account action \"%s\"", op)
        #redirect = "%s?error=%s" % (redirect, "Action is unknown")
    #except:
        #logger.exception("account_actions")

    #return HttpResponseRedirect(redirect)


#@admin_user_required
#def account(request, search_query):
    #"""Account details view."""
    #logging.info("Admin search by %s: %s", request.user_uniq, search_query)
    #show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    #error = request.GET.get('error', None)

    ## By default we consider that the account exists
    #account_exists = True

    ## We may query the database for various stuff, so we will keep the original
    ## query here.
    #original_search_query = search_query

    #account_name = ""
    #account_email = ""
    #account = ""
    #vms = []
    #networks = []
    #is_ip = IP_SEARCH_REGEX.match(search_query)
    #is_vm = VM_SEARCH_REGEX.match(search_query)

    #if is_ip:
        ## Search the IPAddressLog for the full use history of this IP
        #return search_by_ip(request, search_query)
    #elif is_vm:
        #vmid = is_vm.groupdict().get('vmid')
        #try:
            #vm = VirtualMachine.objects.get(pk=int(vmid))
            #search_query = vm.userid
        #except ObjectDoesNotExist:
            #account_exists = False
            #account = None
            #search_query = vmid

    #if account_exists:
        #user = get_user(search_query)
        #if user:
            #account = user.uuid
            #account_email = user.email
            #account_name = user.realname
        #else:
            #account_exists = False

    #if account_exists:
        #filter_extra = {}
        #if not show_deleted:
            #filter_extra['deleted'] = False

        ## all user vms
        #vms = VirtualMachine.objects.filter(
            #userid=account, **filter_extra).order_by('deleted')
        ## return all user private and public networks
        #public_networks = Network.objects.filter(
            #public=True, nics__machine__userid=account,
            #**filter_extra).order_by('state').distinct()
        #private_networks = Network.objects.filter(
            #userid=account, **filter_extra).order_by('state')
        #networks = list(public_networks) + list(private_networks)

    #user_context = {
        #'account_exists': account_exists,
        #'error': error,
        #'is_ip': is_ip,
        #'is_vm': is_vm,
        #'account': account,
        #'search_query': original_search_query,
        #'vms': vms,
        #'show_deleted': show_deleted,
        #'usermodel': user,
        #'account_mail': account_email,
        #'account_name': account_name,
        #'account_accepted': user.is_active,
        #'token': request.user['access']['token']['id'],
        #'networks': networks,
        #'available_ops': [
            #'activate', 'deactivate', 'accept', 'reject', 'verify', 'contact'],
        #'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
        #'UI_MEDIA_URL': UI_MEDIA_URL
    #}

    #return direct_to_template(request, "admin/account.html",
                              #extra_context=user_context)

# Copyright 2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import logging
import re
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.logic import users

from astakos.api.quotas import get_quota_usage
from astakos.im.functions import send_plain as send_email

from eztables.views import DatatablesView
from actions import (AdminAction, AdminActionUnknown, AdminActionNotPermitted,
                     noop)

UUID_SEARCH_REGEX = re.compile('([0-9a-z]{8}-([0-9a-z]{4}-){3}[0-9a-z]{12})')
SHOW_DELETED_VMS = getattr(settings, 'ADMIN_SHOW_DELETED_VMS', False)

templates = {
    'list': 'admin/user_list.html',
    'details': 'admin/user_details.html',
}


def get_user(query):
    """Get AstakosUser from query.

    The query can either be a user email or a UUID.
    """
    is_uuid = UUID_SEARCH_REGEX.match(query)

    try:
        if is_uuid:
            user = AstakosUser.objects.get(uuid=query)
        else:
            user = AstakosUser.objects.get(email=query)
    except ObjectDoesNotExist:
        logging.info("Failed to resolve '%s' into account" % query)
        return None

    return user


def get_allowed_actions(user):
    """Get a list of actions that can apply to a user."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(user):
            allowed_actions.append(key)

    return allowed_actions


def get_enabled_providers(user):
    """Get a comma-seperated string with the user's enabled providers."""
    ep = [prov.module for prov in user.get_enabled_auth_providers()]
    return ", ".join(ep)


def get_user_groups(user):
    groups = ', '.join([g.name for g in user.groups.all()])
    if groups == '':
        return 'None'
    return groups


def get_suspended_vms(user):
    vms = VirtualMachine.objects.filter(userid=user.uuid, suspended=True)
    return map(lambda x: x.name, list(vms))


class UserJSONView(DatatablesView):
    model = AstakosUser
    fields = ('uuid', 'email', 'first_name', 'last_name', 'is_active',
              'is_rejected', 'moderated', 'email_verified')

    extra = True

    def get_extra_data_row(self, inst):
        extra_dict = OrderedDict()
        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(inst),
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
        extra_dict['contact_mail'] = {
            'display_name': "Contact mail",
            'value': inst.email,
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': inst.realname,
            'visible': False,
        }
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

        if users.check_accept(inst):
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

        vms = get_suspended_vms(inst)
        if vms:
            extra_dict['suspended_vms'] = {
                'display_name': "Suspended VMs",
                'value': ', '.join(vms),
                'visible': True,
            }

        return extra_dict


class UserAction(AdminAction):

    """Class for actions on users. Derived from AdminAction.

    Pre-determined Attributes:
        target:        user
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='user', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on users.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['activate'] = UserAction(name='Activate', f=users.activate,
                                     c=users.check_activate,
                                     karma='good', reversible=True)

    actions['deactivate'] = UserAction(name='Deactivate', f=users.deactivate,
                                       c=users.check_deactivate,
                                       karma='bad', reversible=True)

    actions['accept'] = UserAction(name='Accept', f=users.accept,
                                   c=users.check_accept,
                                   karma='good', reversible=False)

    actions['reject'] = UserAction(name='Reject', f=users.reject,
                                   c=users.check_reject,
                                   karma='bad', reversible=False)

    actions['verify'] = UserAction(name='Verify', f=users.verify,
                                   c=users.check_verify,
                                   karma='good', reversible=False)

    actions['resend_verification'] = UserAction(name='Resend verification',
                                                f=noop, karma='good',
                                                c=users.check_verify,
                                                reversible=False)

    actions['contact'] = UserAction(name='Send e-mail', f=send_email)
    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    user = get_user(id)
    actions = generate_actions()
    logging.info("Op: %s, target: %s, fun: %s", op, user.email, actions[op].f)

    if op == 'reject':
        actions[op].f(user, 'Rejected by the admin')
    elif op == 'contact':
        actions[op].f(user, request.POST['text'])
    else:
        actions[op].f(user)


def catalog(request):
    """List view for Astakos users."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Column 1", "E-mail", "First Name", "Last Name",
                          "Active", "Rejected", "Moderated", "Verified",
                          "Details", "Summary"]
    context['item_type'] = 'user'

    return context


def get_quotas(user):
    """Transform the usage dictionary, as retrieved from api.quotas.

    Return a list of dictionaries that represent the quotas of the user. Each
    dictionary has the following form:

    {
        'project': <Project instance>,
        'resources': [('Resource Name1', <Resource dict>),
                      ('Resource Name2', <Resource dict>),...]
    }

    where 'Resource Name' is the name of the resource and <Resource dict> is
    the dictionary that is returned by get_quota_usage and has the following
    fields:

        pending, project_pending, project_limit, project_usage, usage.

    Note, the get_quota_usage function returns many dicts, but we only keep the
    ones that have project_limit > 0
    """
    usage = get_quota_usage(user)

    quotas = []
    for project_id, resource_dict in usage.iteritems():
        source = {}
        source['project'] = Project.objects.get(uuid=project_id)
        q_res = source['resources'] = []

        for resource_name, resource in resource_dict.iteritems():
            if resource['project_limit'] == 0:
                continue
            else:
                q_res.append((resource_name, resource))

        quotas.append(source)

    return quotas


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)
    logging.info("Here")

    user = get_user(query)
    quotas = get_quotas(user)

    project_memberships = ProjectMembership.objects.filter(person=user)
    projects = map(lambda p: p.project, project_memberships)

    vms = VirtualMachine.objects.filter(
        userid=user.uuid).order_by('deleted')

    filter_extra = {}
    show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    if not show_deleted:
        filter_extra['deleted'] = False

    public_networks = Network.objects.filter(
        public=True, nics__machine__userid=user.uuid,
        **filter_extra).order_by('state').distinct()
    private_networks = Network.objects.filter(
        userid=user.uuid, **filter_extra).order_by('state')
    networks = list(public_networks) + list(private_networks)
    logging.info("Networks are: %s", networks)

    context = {
        'main_item': user,
        'main_type': 'user',
        'associations_list': [
            (quotas, 'quota'),
            (projects, 'project'),
            (vms, 'vm'),
            (networks, 'network'),
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

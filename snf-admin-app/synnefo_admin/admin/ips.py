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

from synnefo.db.models import IPAddress
from synnefo.logic import ips
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
from actions import (AdminAction, AdminActionUnknown, AdminActionNotPermitted,
                     noop)
import django_filters

import synnefo_admin.admin.vms as vm_views

templates = {
    'list': 'admin/ip_list.html',
    'details': 'admin/ip_details.html',
}


class IPFilterSet(django_filters.FilterSet):

    """A collection of filters for volumes.

    This filter collection is based on django-filter's FilterSet.
    """

    address = django_filters.CharFilter(label='Address',
                                        lookup_type='icontains')
    owner_name = django_filters.CharFilter(label='Owner Name',
                                           action=vm_views.filter_owner_name)
    userid = django_filters.CharFilter(label='Owner UUID',
                                       lookup_type='icontains')

    class Meta:
        model = IPAddress
        fields = ('id', 'address', 'floating_ip', 'owner_name', 'userid',)


def get_allowed_actions(ip):
    """Get a list of actions that can apply to a ip."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(ip):
            allowed_actions.append(key)

    return allowed_actions


def get_contact_mail(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).email,


def get_contact_name(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).realname,


class IPJSONView(DatatablesView):
    model = IPAddress
    fields = ('pk', 'pk', 'address', 'floating_ip', 'created', 'userid',)

    extra = True
    filters = IPFilterSet

    def get_extra_data_row(self, inst):
        extra_dict = {
            'allowed_actions': {
                'display_name': "",
                'value': get_allowed_actions(inst),
                'visible': False,
            }, 'id': {
                'display_name': "ID",
                'value': inst.pk,
                'visible': False,
            }, 'item_name': {
                'display_name': "Name",
                'value': inst.address,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['ip', inst.pk]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': get_contact_mail(inst),
                'visible': True,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': get_contact_name(inst),
                'visible': True,
            }, 'updated': {
                'display_name': "Update date",
                'value': inst.updated,
                'visible': True,
            }, 'in_use': {
                'display_name': "Currently in Use",
                'value': inst.in_use(),
                'visible': True,
            }, 'network_info': {
                'display_name': "Network info",
                'value': ('ID: ' + str(inst.network.id) + ', Name: ' +
                          str(inst.network.id)),
                'visible': True,
            }
        }

        return extra_dict


class IPAction(AdminAction):

    """Class for actions on ips. Derived from AdminAction.

    Pre-determined Attributes:
        target:        ip
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='ip', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on ips.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['delete'] = IPAction(name='Delete', f=ips.delete_floating_ip,
                                 karma='bad', reversible=False)

    actions['reassign'] = IPAction(name='Reassign to project', f=noop,
                                   karma='neutral', reversible=True)

    actions['contact'] = IPAction(name='Send e-mail', f=send_email)
    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified ip."""
    ip = IPAddress.objects.get(id=id)
    actions = generate_actions()

    if op == 'contact':
        actions[op].f(ip, request.POST['text'])
    else:
        actions[op].f(ip)


def catalog(request):
    """List view for Cyclades ips."""
    context = {}
    context['action_dict'] = generate_actions()
    context['filter_dict'] = IPFilterSet().filters.itervalues()
    context['columns'] = ["Column 1", "ID", "Address", "Floating",
                          "Creation date", "User ID", "Details", "Summary"]
    context['item_type'] = 'ip'

    return context


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    ip = IPAddress.objects.get(pk=int(query))
    vm_list = [ip.nic.machine]
    network_list = [ip.nic.network]
    nic_list = [ip.nic]
    user_list = AstakosUser.objects.filter(uuid=ip.userid)
    project_list = Project.objects.filter(uuid=ip.project)

    context = {
        'main_item': ip,
        'main_type': 'ip',
        'associations_list': [
            (vm_list, 'vm'),
            (network_list, 'network'),
            (nic_list, 'nic'),
            (user_list, 'user'),
            (project_list, 'project'),
        ]
    }

    return context

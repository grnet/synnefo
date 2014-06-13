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

from synnefo.db.models import (Network, VirtualMachine, NetworkInterface,
                               IPAddress)
from synnefo.logic.networks import validate_network_action
from synnefo.logic import networks
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
from actions import (AdminAction, AdminActionUnknown, AdminActionNotPermitted,
                     noop, has_permission_or_403)

import django_filters

import vms as vm_views
import users as user_views
import ips as ip_views
import projects as project_views


templates = {
    'list': 'admin/network_list.html',
    'details': 'admin/network_details.html',
}


def get_network(query):
    return Network.objects.get(pk=int(query))


class NetworkFilterSet(django_filters.FilterSet):

    """A collection of filters for VMs.

    This filter collection is based on django-filter's FilterSet.
    """

    name = django_filters.CharFilter(label='Name', lookup_type='icontains')
    state = django_filters.MultipleChoiceFilter(
        label='Status', name='state', choices=Network.OPER_STATES)
    owner_name = django_filters.CharFilter(label='Owner Name',
                                           action=vm_views.filter_owner_name)
    userid = django_filters.CharFilter(label='Owner UUID',
                                       lookup_type='icontains')

    class Meta:
        model = Network
        fields = ('id', 'name', 'state', 'public', 'drained', 'owner_name',
                  'userid',)


def get_allowed_actions(network):
    """Get a list of actions that can apply to a network."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(network):
            allowed_actions.append(key)

    return allowed_actions


def get_contact_mail(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).email,


def get_contact_name(inst):
    if inst.userid:
        return AstakosUser.objects.get(uuid=inst.userid).realname,


class NetworkJSONView(DatatablesView):
    model = Network
    fields = ('pk', 'name', 'state', 'public', 'drained',)

    extra = True
    filters = NetworkFilterSet

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
                'value': inst.name,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['network', inst.id]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': get_contact_mail(inst),
                'visible': False,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': get_contact_name(inst),
                'visible': False,
            }, 'public': {
                'display_name': "Public",
                'value': inst.public,
                'visible': True,
            }, 'updated': {
                'display_name': "Update time",
                'value': inst.updated,
                'visible': True,
            }
        }

        return extra_dict


class NetworkAction(AdminAction):

    """Class for actions on networks. Derived from AdminAction.

    Pre-determined Attributes:
        target:        network
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='network', f=f, **kwargs)


def drain_network(network):
    logging.info("Draining network")
    network.drained = True
    network.save()


def undrain_network(network):
    network.drained = False
    network.save()


def check_network_action(action):
    return lambda n: validate_network_action(n, action)


def generate_actions():
    """Create a list of actions on networks.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['drain'] = NetworkAction(name='Drain', f=drain_network,
                                     #c=check_network_action('DRAIN'),
                                     reversible=True,
                                     allowed_groups=['superadmin'])

    actions['undrain'] = NetworkAction(name='Undrain', f=undrain_network,
                                       #c=check_network_action('UNDRAIN'),
                                       karma='neutral', reversible=True,
                                       allowed_groups=['superadmin'])

    actions['delete'] = NetworkAction(name='Delete', f=networks.delete,
                                      c=check_network_action('DESTROY'),
                                      karma='bad', reversible=False,
                                      allowed_groups=['superadmin'])

    actions['reassign'] = NetworkAction(name='Reassign to project', f=noop,
                                        karma='neutral', reversible=True,
                                        allowed_groups=['superadmin'])

    actions['change_owner'] = NetworkAction(name='Change owner', f=noop,
                                            karma='neutral', reversible=True,
                                            allowed_groups=['superadmin'])

    actions['contact'] = NetworkAction(name='Send e-mail', f=send_email,
                                       allowed_groups=['admin', 'superadmin'])
    return actions


def get_permitted_actions(user):
    actions = generate_actions()
    for key, action in actions.iteritems():
        if not action.is_user_allowed(user):
            actions.pop(key, None)
    return actions


@has_permission_or_403(generate_actions())
def do_action(request, op, id):
    """Apply the requested action on the specified network."""
    network = Network.objects.get(pk=id)
    actions = get_permitted_actions(request.user)

    if op == 'contact':
        actions[op].f(network, request.POST['text'])
    else:
        actions[op].f(network)


def catalog(request):
    """List view for Cyclades networks."""
    context = {}
    context['action_dict'] = get_permitted_actions(request.user)
    context['filter_dict'] = NetworkFilterSet().filters.itervalues()
    context['columns'] = ["ID", "Name", "Status", "Public",
                          "Drained", ""]
    context['item_type'] = 'network'

    return context


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    network = get_network(query)
    vm_list = network.machines.all()
    nic_list = NetworkInterface.objects.filter(network=network)
    ip_list = IPAddress.objects.filter(network=network)
    user_list = AstakosUser.objects.filter(uuid=network.userid)
    project_list = Project.objects.filter(uuid=network.project)

    context = {
        'main_item': network,
        'main_type': 'network',
        'associations_list': [
            (vm_list, 'vm'),
            (nic_list, 'nic'),
            (ip_list, 'ip'),
            (user_list, 'user'),
            (project_list, 'project'),
        ]
    }

    return context

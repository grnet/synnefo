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

from operator import or_

from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from actions import AdminAction, noop

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.user_utils import send_plain as send_email

from synnefo.logic import servers as servers_backend
from synnefo.logic.commands import validate_server_action

from eztables.views import DatatablesView

import django_filters
from django.db.models import Q

from .users import filter_name as get_users_by_name

templates = {
    'list': 'admin/vm_list.html',
    'details': 'admin/vm_details.html',
}


def get_vm(query):
    try:
        id = query.translate(None, 'vm-')
    except Exception:
        id = query
    return VirtualMachine.objects.get(pk=int(id))


def filter_owner_name(queryset, search):
    users = get_users_by_name(AstakosUser.objects.all(), search).values('uuid')
    criterions = [Q(userid=user['uuid']) for user in users]
    if not criterions:
        return queryset.none()
    qor = reduce(or_, criterions)
    return queryset.filter(qor)


class VMFilterSet(django_filters.FilterSet):

    """A collection of filters for VMs.

    This filter collection is based on django-filter's FilterSet.
    """

    name = django_filters.CharFilter(label='Name', lookup_type='icontains')
    owner_name = django_filters.CharFilter(label='Owner Name',
                                           action=filter_owner_name)
    userid = django_filters.CharFilter(label='Owner UUID',
                                       lookup_type='icontains')
    imageid = django_filters.CharFilter(label='Image UUID',
                                        lookup_type='icontains')

    class Meta:
        model = VirtualMachine
        fields = ('operstate', 'name', 'owner_name', 'userid', 'imageid')


def get_allowed_actions(vm):
    """Get a list of actions that can apply to a user."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(vm):
            allowed_actions.append(key)

    return allowed_actions


def get_flavor_info(vm):
    return ('CPU: ' + str(vm.flavor.cpu) + ', RAM: ' + str(vm.flavor.ram) +
            ', Disk size: ' + str(vm.flavor.disk) + ', Disk template: ' +
            str(vm.flavor.volume_type.disk_template))


class VMJSONView(DatatablesView):
    model = VirtualMachine
    fields = ('pk', 'pk', 'name', 'operstate', 'suspended',)

    extra = True
    filters = VMFilterSet

    def get_extra_data_row(self, inst):
        extra_dict = OrderedDict()
        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(inst),
            'visible': False,
        }
        extra_dict['id'] = {
            'display_name': "ID",
            'value': inst.pk,
            'visible': False,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': inst.name,
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['vm', inst.pk]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': inst.userid,
            'visible': False,
        }
        extra_dict['contact_mail'] = {
            'display_name': "Contact mail",
            'value': AstakosUser.objects.get(uuid=inst.userid).email,
            'visible': True,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': AstakosUser.objects.get(uuid=inst.userid).realname,
            'visible': True,
        }
        extra_dict['user_id'] = {
            'display_name': "User ID",
            'value': inst.userid,
            'visible': True,
        }
        extra_dict['image_id'] = {
            'display_name': "Image ID",
            'value': inst.imageid,
            'visible': True,
        }
        extra_dict['flavor_info'] = {
            'display_name': "Flavor info",
            'value': get_flavor_info(inst),
            'visible': True,
        }
        extra_dict['created'] = {
            'display_name': "Created",
            'value': inst.created,
            'visible': True,
        }
        extra_dict['updated'] = {
            'display_name': "Updated",
            'value': inst.updated,
            'visible': True,
        }
        #extra_dict['suspended'] = {
            #'display_name': "Suspended",
            #'value': inst.suspended,
            #'visible': True,
        #}

        return extra_dict


class VMAction(AdminAction):

    """Class for actions on VMs. Derived from AdminAction.

    Pre-determined Attributes:
        target:        vm
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='vm', f=f, **kwargs)


def vm_suspend(vm):
    """Suspend a VM."""
    vm.suspended = True
    vm.save()


def vm_suspend_release(vm):
    """Release previous VM suspension."""
    vm.suspended = False
    vm.save()


def check_vm_action(action):
    if action == 'SUSPEND':
        return lambda vm: not vm.suspended
    elif action == 'RELEASE':
        return lambda vm: vm.suspended
    else:
        return lambda vm: validate_server_action(vm, action)


def generate_actions():
    """Create a list of actions on users.

    The actions are: start/shutdown, restart, destroy,
                     suspend/release, reassign, contact
    """
    actions = OrderedDict()

    actions['start'] = VMAction(name='Start', f=servers_backend.start,
                                c=check_vm_action('START'),
                                karma='good', reversible=True)

    actions['shutdown'] = VMAction(name='Shutdown', f=servers_backend.stop,
                                   c=check_vm_action('STOP'), karma='bad',
                                   reversible=True)

    actions['reboot'] = VMAction(name='Reboot', f=servers_backend.reboot,
                                 c=check_vm_action('REBOOT'), karma='bad',
                                 reversible=True)

    actions['resize'] = VMAction(name='Resize', f=noop,
                                 c=check_vm_action('RESIZE'), karma='neutral',
                                 reversible=False)

    actions['destroy'] = VMAction(name='Destroy', f=servers_backend.destroy,
                                  c=check_vm_action('DESTROY'), karma='bad',
                                  reversible=False)

    actions['connect'] = VMAction(name='Connect to network', f=noop,
                                  karma='good', reversible=True)

    actions['disconnect'] = VMAction(name='Disconnect from network', f=noop,
                                     karma='bad', reversible=True)

    actions['attach'] = VMAction(name='Attach IP', f=noop,
                                 c=check_vm_action('ADDFLOATINGIP'),
                                 karma='good', reversible=True)

    actions['detach'] = VMAction(name='Detach IP', f=noop,
                                 c=check_vm_action('REMOVEFLOATINGIP'),
                                 karma='bad', reversible=True)

    actions['suspend'] = VMAction(name='Suspend', f=vm_suspend,
                                  c=check_vm_action('SUSPEND'),
                                  karma='bad', reversible=True)

    actions['release'] = VMAction(name='Release suspension',
                                  f=vm_suspend_release,
                                  c=check_vm_action('RELEASE'), karma='good',
                                  reversible=True)

    actions['reassign'] = VMAction(name='Reassign to project', f=noop,
                                   karma='neutral', reversible=True)

    actions['change_owner'] = VMAction(name='Change owner', f=noop,
                                       karma='neutral', reversible=True)

    actions['contact'] = VMAction(name='Send e-mail', f=send_email)

    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    vm = VirtualMachine.objects.get(pk=id)
    actions = generate_actions()
    logging.info("Op: %s, vm: %s, fun: %s", op, vm.pk, actions[op].f)

    if op == 'reboot':
        actions[op].f(vm, "SOFT")
    elif op == 'contact':
        user = AstakosUser.objects.get(uuid=vm.userid)
        actions[op].f(user, request.POST['text'])
    else:
        actions[op].f(vm)


def catalog(request):
    """List view for Cyclades VMs."""
    logging.info("Filters are %s", VMFilterSet().filters)
    context = {}
    context['action_dict'] = generate_actions()
    context['filter_dict'] = VMFilterSet().filters.itervalues()
    context['columns'] = ["Column 1", "ID", "Name", "State", "Suspended",
                          "Details", "Summary"]
    context['item_type'] = 'vm'

    return context


def details(request, query):
    """Details view for Astakos users."""
    vm = get_vm(query)
    user_list = AstakosUser.objects.filter(uuid=vm.userid)
    project_list = Project.objects.filter(uuid=vm.project)
    volume_list = vm.volumes.all()
    network_list = Network.objects.filter(machines__pk=vm.pk)
    nic_list = vm.nics.all()
    ip_list = [nic.ips.all() for nic in nic_list]
    ip_list = reduce(or_, ip_list) if ip_list else ip_list

    context = {
        'main_item': vm,
        'main_type': 'vm',
        'associations_list': [
            (user_list, 'user'),
            (project_list, 'project'),
            (volume_list, 'volume'),
            (network_list, 'network'),
            (nic_list, 'nic'),
            (ip_list, 'ip'),
        ]
    }

    return context

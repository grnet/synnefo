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

from synnefo.db.models import Volume
from astakos.im.functions import send_plain as send_email
from astakos.im.models import AstakosUser

from eztables.views import DatatablesView
from actions import AdminAction, AdminActionUnknown, AdminActionNotPermitted

templates = {
    'list': 'admin/volume_list.html',
    'details': 'admin/volume_details.html',
}


def get_allowed_actions(volume):
    """Get a list of actions that can apply to a volume."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(volume):
            allowed_actions.append(key)

    return allowed_actions


class VolumeJSONView(DatatablesView):
    model = Volume
    fields = ('id',
              'id',
              'name',
              'status',
              'created',
              'machine__pk',
              )

    extra = True

    def get_extra_data_row(self, inst):
        logging.info("I am here")
        extra_dict = {
            'allowed_actions': {
                'display_name': "",
                'value': get_allowed_actions(inst),
                'visible': False,
            }, 'id': {
                'display_name': "ID",
                'value': inst.id,
                'visible': False,
            }, 'item_name': {
                'display_name': "Name",
                'value': inst.name,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['volume', inst.id]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': inst.userid,
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': AstakosUser.objects.get(uuid=inst.userid).email,
                'visible': False,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': AstakosUser.objects.get(uuid=inst.userid).realname,
                'visible': False,
            }, 'description': {
                'display_name': "Description",
                'value': inst.description,
                'visible': True,
            }, 'updated': {
                'display_name': "Update time",
                'value': inst.updated,
                'visible': True,
            }, 'user_info': {
                'display_name': "User info",
                'value': inst.userid,
                'visible': True,
            }
        }

        return extra_dict


class VolumeAction(AdminAction):

    """Class for actions on volumes. Derived from AdminAction.

    Pre-determined Attributes:
        target:        volume
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='volume', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on volumes.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['contact'] = VolumeAction(name='Send e-mail', f=send_email)
    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified volume."""
    volume = Volume.objects.get(id=id)
    actions = generate_actions()

    if op == 'contact':
        actions[op].f(volume, request.POST['text'])
    else:
        actions[op].f(volume)


def catalog(request):
    """List view for Cyclades volumes."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Column 1", "ID", "Name", "Status", "Creation date",
                          "VM ID", "Details", "Summary"]
    context['item_type'] = 'volume'

    return context


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

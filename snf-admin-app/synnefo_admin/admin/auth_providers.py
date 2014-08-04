import logging
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
#

import re
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse

from astakos.im.models import AstakosUserAuthProvider
from astakos.im.models import AstakosUser

from eztables.views import DatatablesView
from actions import AdminAction, AdminActionUnknown, AdminActionNotPermitted

templates = {
    'list': 'admin/auth_provider_list.html',
    'details': 'admin/auth_provider_details.html',
}


def get_allowed_actions(auth_provider):
    """Get a list of actions that can apply to an auth_provider."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(auth_provider):
            allowed_actions.append(key)

    return allowed_actions


class AstakosUserAuthProviderJSONView(DatatablesView):
    model = AstakosUserAuthProvider
    fields = ('id', 'module', 'identifier', 'active', 'created')

    extra = True

    def get_extra_data_row(self, inst):
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
                'value': inst.module,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': (reverse('admin-details', args=['auth_provider',
                                                         inst.id])),
                'visible': True,
            }, 'contact_email': {
                'display_name': "Contact email",
                'value': None,
                'visible': False,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': None,
                'visible': False,
            }, 'description': {
                'display_name': "Description",
                'value': inst.info_data,
                'visible': True,
            }, 'auth_backend': {
                'display_name': "Auth backend",
                'value': inst.auth_backend,
                'visible': True,
            }
        }

        return extra_dict


class AstakosUserAuthProviderAction(AdminAction):

    """Class for actions on auth_providers. Derived from AdminAction.

    Pre-determined Attributes:
        target:        auth_provider
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='auth_provider', f=f,
                             **kwargs)


def generate_actions():
    """Create a list of actions on auth_providers.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['contact'] = AstakosUserAuthProviderAction(name='Send e-mail',
                                                       f=send_email)
    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified auth_provider."""
    auth_provider = AstakosUserAuthProvider.objects.get(id=id)
    actions = generate_actions()

    if op == 'contact':
        actions[op].apply(auth_provider, request.POST['text'])
    else:
        actions[op].apply(auth_provider)


def catalog(request):
    """List view for Cyclades auth_providers."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Name", "Identifier", "Active",
                          "Creation date", ""]
    context['item_type'] = 'auth_provider'

    return context

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
            }, 'contact_mail': {
                'display_name': "Contact mail",
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
        actions[op].f(auth_provider, request.POST['text'])
    else:
        actions[op].f(auth_provider)


def catalog(request):
    """List view for Cyclades auth_providers."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Column 1", "Name", "Identifier", "Active",
                          "Creation date", "Details", "Summary"]
    context['item_type'] = 'auth_provider'

    return context

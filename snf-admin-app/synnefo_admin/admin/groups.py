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
from django.contrib.auth.models import Group

from astakos.im.functions import send_plain as send_email
from astakos.im.models import AstakosUser

from eztables.views import DatatablesView
from actions import AdminAction, AdminActionUnknown, AdminActionNotPermitted

templates = {
    'list': 'admin/group_list.html',
    'details': 'admin/group_details.html',
}


def get_allowed_actions(group):
    """Get a list of actions that can apply to a group."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(group):
            allowed_actions.append(key)

    return allowed_actions


class GroupJSONView(DatatablesView):
    model = Group
    fields = ('id', 'id', 'name')

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
                'value': inst.name,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['group', inst.id]),
                'visible': True,
            }
        }

        return extra_dict


class GroupAction(AdminAction):

    """Class for actions on groups. Derived from AdminAction.

    Pre-determined Attributes:
        target:        group
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='group', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on groups.

    Currently there are none
    """
    actions = OrderedDict()

    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified group."""
    group = Group.objects.get(id=id)
    actions = generate_actions()

    if op == 'contact':
        actions[op].f(group, request.POST['text'])
    else:
        actions[op].f(group)


def catalog(request):
    """List view for Cyclades groups."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Column 1", "ID", "Name", "Details", "Summary"]
    context['item_type'] = 'group'

    return context

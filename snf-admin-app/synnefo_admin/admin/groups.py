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
import re
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group

from synnefo_admin.admin.exceptions import AdminHttp404

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
    fields = ('id', 'name')

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
            },
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
        actions[op].apply(group, request.POST['text'])
    else:
        actions[op].apply(group)


def catalog(request):
    """List view for Cyclades groups."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["ID", "Name", ""]
    context['item_type'] = 'group'

    return context


def details(request, query):
    """Details view for Cyclades groups."""
    raise AdminHttp404("There are no details for Groups")

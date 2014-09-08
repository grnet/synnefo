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

from django.contrib.auth.models import Group

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.tables import AdminJSONView


templates = {
    'list': 'admin/group_list.html',
    'details': 'admin/group_details.html',
}


class GroupJSONView(AdminJSONView):
    model = Group
    fields = ('id', 'name')

    extra = True

    def get_extra_data_row(self, inst):
        extra_dict = {
            'allowed_actions': {
                'display_name': "",
                'value': [],
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


JSON_CLASS = GroupJSONView


def do_action(request, op, id):
    raise AdminHttp404("There are no actions for Groups")


def catalog(request):
    """List view for Cyclades groups."""
    context = {}
    context['action_dict'] = {}
    context['columns'] = ["ID", "Name", ""]
    context['item_type'] = 'group'

    return context


def details(request, query):
    """Details view for Cyclades groups."""
    raise AdminHttp404("There are no details for Groups")

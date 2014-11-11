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

from django.core.urlresolvers import reverse

from astakos.im.models import AstakosUserAuthProvider
from synnefo_admin.admin.tables import AdminJSONView

templates = {
    'list': 'admin/auth_provider_list.html',
    'details': 'admin/auth_provider_details.html',
}


class AstakosUserAuthProviderJSONView(AdminJSONView):
    model = AstakosUserAuthProvider
    fields = ('id', 'module', 'identifier', 'active', 'created')

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


JSON_CLASS = AstakosUserAuthProviderJSONView


def catalog(request):
    """List view for Cyclades auth_providers."""
    context = {}
    context['action_dict'] = {}
    context['columns'] = ["Name", "Identifier", "Active",
                          "Creation date", ""]
    context['item_type'] = 'auth_provider'

    return context

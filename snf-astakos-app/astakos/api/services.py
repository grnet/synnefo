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


astakos_services = {
    'astakos_account': {
        'type': 'account',
        'component': 'astakos',
        'prefix': 'account',
        'public': True,
        'endpoints': [
            {'versionId': 'v1.0',
             'publicURL': None},
        ],
        'resources': {
            'pending_app': {
                'desc': "Number of pending project applications",
                'name': "astakos.pending_app",
                'service_type': "account",
                'service_origin': "astakos_account",
                'ui_visible': False,
                'api_visible': False},
        },
    },

    'astakos_identity': {
        'type': 'identity',
        'component': 'astakos',
        'prefix': 'identity',
        'public': True,
        'endpoints': [
            {'versionId': 'v2.0',
             'publicURL': None},
        ],
        'resources': {},
    },

    'astakos_weblogin': {
        'type': 'astakos_weblogin',
        'component': 'astakos',
        'prefix': 'weblogin',
        'public': True,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
    },

    'astakos_ui': {
        'type': 'astakos_ui',
        'component': 'astakos',
        'prefix': 'ui',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
    },

    'astakos_admin': {
        'type': 'astakos_admin',
        'component': 'astakos',
        'prefix': 'admin',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
        'resources': {},
    },
}

from astakos.oa2.services import oa2_services
astakos_services.update(oa2_services)

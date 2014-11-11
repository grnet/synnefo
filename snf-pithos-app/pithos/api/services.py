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


pithos_services = {
    'pithos_object-store': {
        'type': 'object-store',
        'component': 'pithos',
        'prefix': 'object-store',
        'public': True,
        'endpoints': [
            {'versionId': 'v1',
             'publicURL': None},
        ],
        'resources': {
            'diskspace': {
                "desc": "Pithos account diskspace",
                "name": "pithos.diskspace",
                "unit": "bytes",
                "service_type": "object-store",
                "service_origin": "pithos_object-store",
            },
        },
    },

    'pithos_public': {
        'type': 'pithos_public',
        'component': 'pithos',
        'prefix': 'public',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
        'resources': {},
    },

    'pithos_ui': {
        'type': 'pithos_ui',
        'component': 'pithos',
        'prefix': 'ui',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
        'resources': {},
    },
}

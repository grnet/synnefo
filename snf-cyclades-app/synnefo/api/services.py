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


# Required but undefined fields are given a value of None

cyclades_services = {
    'cyclades_compute': {
        'type': 'compute',
        'component': 'cyclades',
        'prefix': 'compute',
        'public': True,
        'endpoints': [
            {'versionId': 'v2.0',
             'publicURL': None},
        ],
        'resources': {
            'vm': {
                "name": "cyclades.vm",
                "desc": "Number of virtual machines",
                "service_type": "compute",
                "service_origin": "cyclades_compute",
            },
            'total_cpu': {
                "name": "cyclades.total_cpu",
                "desc": "Number of virtual machine processors",
                "service_type": "compute",
                "service_origin": "cyclades_compute",
                "ui_visible": False,
                "api_visible": False,
            },
            'cpu': {
                "name": "cyclades.cpu",
                "desc": "Number of virtual machine processors of running"
                        " servers",
                "service_type": "compute",
                "service_origin": "cyclades_compute",
            },
            'total_ram': {
                "name": "cyclades.total_ram",
                "desc": "Virtual machine memory size",
                "unit": "bytes",
                "service_type": "compute",
                "service_origin": "cyclades_compute",
                "ui_visible": False,
                "api_visible": False,
            },
            'ram': {
                "name": "cyclades.ram",
                "desc": "Virtual machine memory size of running servers",
                "unit": "bytes",
                "service_type": "compute",
                "service_origin": "cyclades_compute",
            },
            'disk': {
                "name": "cyclades.disk",
                "desc": "Virtual machine disk size",
                "unit": "bytes",
                "service_type": "compute",
                "service_origin": "cyclades_compute",
            },
        },
    },

    'cyclades_plankton': {
        'type': 'image',
        'component': 'cyclades',
        'prefix': 'image',
        'public': True,
        'endpoints': [
            {'versionId': 'v1.0',
             'publicURL': None},
        ],
        'resources': {},
    },

    'cyclades_network': {
        'type': 'network',
        'component': 'cyclades',
        'prefix': 'network',
        'public': True,
        'endpoints': [
            {'versionId': 'v2.0',
             'publicURL': None},
        ],
        'resources': {
            'network-private': {
                "name": "cyclades.network.private",
                "desc": "Number of private networks",
                "service_type": "network",
                "service_origin": "cyclades_network",
            },
            'floating_ip': {
                "name": "cyclades.floating_ip",
                "desc": "Number of Floating IP addresses",
                "service_type": "network",
                "service_origin": "cyclades_network",
            },
        },
    },

    'cyclades_vmapi': {
        'type': 'vmapi',
        'component': 'cyclades',
        'prefix': 'vmapi',
        'public': True,
        'endpoints': [
            {'versionId': 'v1.0',
             'publicURL': None},
        ],
        'resources': {},
    },

    'cyclades_helpdesk': {
        'type': 'cyclades_helpdesk',
        'component': 'cyclades',
        'prefix': 'helpdesk',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
    },

    'cyclades_userdata': {
        'type': 'cyclades_userdata',
        'component': 'cyclades',
        'prefix': 'userdata',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
        'resources': {},
    },

    'cyclades_ui': {
        'type': 'cyclades_ui',
        'component': 'cyclades',
        'prefix': 'ui',
        'public': False,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
        'resources': {},
    },

    'cyclades_admin': {
        'type': 'admin',
        'component': 'cyclades',
        'prefix': 'admin',
        'public': True,
        'endpoints': [
            {'versionId': '',
             'publicURL': None},
        ],
        'resources': {},
    },

    'cyclades_volume': {
        'type': 'volume',
        'component': 'cyclades',
        'prefix': 'volume',
        'public': True,
        'endpoints': [
            {'versionId': 'v2.0',
             'publicURL': None},
        ],
        'resources': {},
    },
}

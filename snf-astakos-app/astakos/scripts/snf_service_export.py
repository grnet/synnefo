import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'
import sys
from optparse import OptionParser
from synnefo.lib.services import fill_endpoints, filter_public
from django.utils import simplejson as json


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
                "ui_visible": False,
                "api_visible": False},
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


definitions = {
    'astakos': astakos_services,
    'cyclades': cyclades_services,
    'pithos': pithos_services,
}


def print_definitions(d, base_url):
    fill_endpoints(d, base_url)
    print json.dumps(filter_public(d), indent=4)


usage = "usage: %prog <component_name> <base_url>"
parser = OptionParser(usage=usage)


def main():
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error("Wrong number of arguments.")
    component = args[0]
    try:
        services = definitions[component]
    except KeyError:
        print >> sys.stderr, "Unrecognized component %s" % component
        exit(1)
    base_url = args[1]
    print_definitions(services, base_url)

if __name__ == '__main__':
    main()

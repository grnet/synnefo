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

from astakos.im import settings
from synnefo.lib.utils import dict_merge

RESOURCES = {
    'groups': {
        'compute': {
            'help_text': ('Compute resources '
                          '(amount of VMs, CPUs, RAM, Hard disk) '),
            'is_abbreviation': False,
            'report_desc': '',
            'verbose_name': 'compute',
        },
        'storage': {
            'help_text': ('Storage resources '
                          '(amount of space to store files on Pithos) '),
            'is_abbreviation': False,
            'report_desc': '',
            'verbose_name': 'storage',
        },
        'network': {
            'help_text': ' Network resources (number of Private Networks)  ',
            'is_abbreviation': False,
            'report_desc': '',
            'verbose_name': 'network',
        },
    },
    'resources': {
        'pithos.diskspace': {
            'help_text': ('This is the space on Pithos for storing files '
                          'and VM Images. '),
            'help_text_input_each': ('This is the maximum amount of space on '
                                     'Pithos that will be granted to each '
                                     'user of this Project '),
            'help_text_input_total': ('This is the total amount of space on '
                                      'Pithos that will be granted for use '
                                      'across all users of this Project '),
            'is_abbreviation': False,
            'report_desc': 'File Storage Space',
            'placeholder': 'eg. 10GB',
            'verbose_name': 'File Storage Space',
            'group': 'storage'
        },
        'cyclades.disk': {
            'help_text': ('This is the Hard Disk that the VMs have that '
                          'run the OS '),
            'help_text_input_each': ("This is the maximum amount of System "
                                     "Disk "
                                     "that will be granted to each user of "
                                     "this Project (this refers to the total "
                                     "Hard Disk of all VMs, not each VM's "
                                     "Hard Disk)"),
            'help_text_input_total': ("This is the total amount of System "
                                      "Disk that will be granted across all "
                                      "users of this Project (this refers to "
                                      "the total Hard Disk of all VMs, not "
                                      "each VM's Hard Disk)"),
            'is_abbreviation': False,
            'report_desc': 'Hard Disk Storage',
            'placeholder': 'eg. 5GB, 2GB etc',
            'verbose_name': 'Hard Disk Storage',
            'group': 'compute'
        },
        'cyclades.total_ram': {
            'help_text': 'RAM used by VMs ',
            'help_text_input_each': ('This is the maximum amount of RAM that '
                                     'will be granted to each user of this '
                                     'Project (on all VMs)  '),
            'help_text_input_total': ('This is the total amount of RAM that '
                                      'will be granted across all users of '
                                      'this Project (on all VMs)'),
            'is_abbreviation': True,
            'report_desc': 'Total RAM',
            'placeholder': 'eg. 4GB',
            'verbose_name': 'Total ram',
            'group': 'compute'

        },
        'cyclades.ram': {
            'help_text': 'RAM used by active VMs ',
            'help_text_input_each': ('This is the maximum amount of RAM that '
                                     'will be granted to each user of this '
                                     'Project (on all active VMs)  '),
            'help_text_input_total': ('This is the total amount of RAM that '
                                      'will be granted across all users of '
                                      'this Project (on all active VMs)'),
            'is_abbreviation': False,
            'report_desc': 'RAM',
            'placeholder': 'eg. 4GB',
            'verbose_name': 'RAM',
            'group': 'compute'

        },
        'cyclades.total_cpu': {
            'help_text': 'CPUs used by VMs ',
            'help_text_input_each': ('This is the maximum number of CPUs that '
                                     'will be granted to each user of this '
                                     'Project (on all VMs)'),
            'help_text_input_total': ('This is the total number of CPUs that '
                                      'will be granted across all users of '
                                      'this Project (on all VMs)'),
            'is_abbreviation': True,
            'report_desc': 'Total CPUs',
            'placeholder': 'eg. 1',
            'verbose_name': 'Total cpu',
            'group': 'compute'

        },
        'cyclades.cpu': {
            'help_text': 'CPUs used by active VMs ',
            'help_text_input_each': ('This is the maximum number of CPUs that '
                                     'will be granted to each user of this '
                                     'Project (on all active VMs)  '),
            'help_text_input_total': ('This is the total number of CPUs that '
                                      'will be granted across all users '
                                      'of this Project (on all active VMs)  '),
            'is_abbreviation': False,
            'report_desc': 'CPUs',
            'placeholder': 'eg. 1',
            'verbose_name': 'CPU',
            'group': 'compute'

        },
        'cyclades.vm': {
            'help_text': ('These are the VMs one can create on the '
                          'Cyclades UI '),
            'help_text_input_each': ('This is the maximum number of VMs that '
                                     'will be granted to each user of this '
                                     'Project '),
            'help_text_input_total': ('This is the total number of VMs that '
                                      'will be granted across all users '
                                      'of this Project in total'),
            'is_abbreviation': True,
            'report_desc': 'Virtual Machines',
            'placeholder': 'eg. 2',
            'verbose_name': 'vm',
            'group': 'compute'

        },
        'cyclades.network.private': {
            'help_text': ('These are the Private Networks one can create on '
                          'the Cyclades UI. '),
            'help_text_input_each': ('This is the maximum number of Private '
                                     'Networks that will be granted to each '
                                     'user of this Project '),
            'help_text_input_total': ('This is the total number of Private '
                                      'Networks that will be granted across '
                                      'all users of this Project'),
            'is_abbreviation': False,
            'report_desc': 'Private Networks',
            'placeholder': 'eg. 1',
            'verbose_name': 'Private Network',
            'group': 'network'

        },
        'cyclades.floating_ip': {
            'help_text': ('These are the Public (Floating) IPs one can '
                          'reserve on the Cyclades UI. '),
            'help_text_input_each': ('This is the maximum number of Public '
                                     '(Floating) IPs that will be granted to '
                                     'each user of this Project '),
            'help_text_input_total': ('This is the number of Public '
                                      '(Floating) IPs that will be granted '
                                      'across all users of this Project'),
            'is_abbreviation': False,
            'report_desc': 'Public (Floating) IPs',
            'placeholder': 'eg. 1',
            'verbose_name': 'Public (Floating) IP',
            'group': 'network'

        },
        'astakos.pending_app': {
            'help_text': ('Pending project applications limit'),
            'help_text_input_each': ('Maximum pending project applications '
                                     'user is allowed to create'),
            'help_text_input_total': ('Total pending project applications '
                                      ' project users are allowed to create '
                                      ' in total'),
            'is_abbreviation': False,
            'report_desc': 'Pending Project Applications',
            'placeholder': 'eg. 2',
            'verbose_name': 'pending project application',
            'group': 'accounts'

        },
    },
    'groups_order': ['storage', 'compute', 'network', 'accounts'],
    'resources_order': ['pithos.diskspace',
                        'cyclades.disk',
                        'cyclades.total_cpu',
                        'cyclades.cpu',
                        'cyclades.total_ram',
                        'cyclades.ram',
                        'cyclades.vm',
                        'cyclades.network.private',
                        'cyclades.floating_ip',
                        'astakos.pending_app'
                        ],
}

# extend from settings
RESOURCES = dict_merge(RESOURCES, settings.RESOURCES_META)


def component_defaults(service_name):
    """
    Metadata for unkown services
    """
    return {
        'name': service_name,
        'order': 1000,
        'verbose_name': service_name.title(),
        'cloudbar': {
            'show': True,
            'title': service_name
        },
        'dashboard': {
            'show': True,
            'order': 1000,
            'description': '%s service' % service_name
        }
    }


COMPONENTS = {
    'astakos': {
        'order': 1,
        'dashboard': {
            'order': 3,
            'show': True,
            'description': "Access the dashboard from the top right corner "
                           "of your screen. Here you can manage your profile, "
                           "see the usage of your resources and manage "
                           "projects to share virtual resources with "
                           "colleagues."
        },
        'cloudbar': {
            'show': False
        }
    },
    'pithos': {
        'order': 2,
        'dashboard': {
            'order': 1,
            'show': True,
            'description': "Pithos is the File Storage service. "
                           "Click to start uploading and managing your "
                           "files on the cloud."
        },
        'cloudbar': {
            'show': True
        }
    },
    'cyclades': {
        'order': 3,
        'dashboard': {
            'order': 2,
            'show': True,
            'description': "Cyclades is the Compute and Network Service. "
                           "Click to start creating Virtual Machines and "
                           "connect them to arbitrary Networks."
        },
        'cloudbar': {
            'show': True
        }
    }
}


PROJECT_MEMBER_JOIN_POLICIES = {
    1: 'automatically accepted',
    2: 'owner accepts',
    3: 'closed',
}


PROJECT_MEMBER_LEAVE_POLICIES = {
    1: 'automatically accepted',
    2: 'owner accepts',
    3: 'closed',
}

USAGE_TAG_MAP = {
    0: 'green',
    33: 'yellow',
    66: 'red'
}

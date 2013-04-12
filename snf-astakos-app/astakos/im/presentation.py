# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

RESOURCES_PRESENTATION_DATA = {
    'groups': {
        'compute': {
            'help_text': ('Compute resources '
                          '(amount of VMs, CPUs, RAM, System disk) '),
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
        'pithos+.diskspace': {
            'help_text': ('This is the space on Pithos for storing files '
                          'and VM Images. '),
            'help_text_input_each': ('This is the total amount of space on '
                                     'Pithos that will be granted to each '
                                     'user of this Project '),
            'is_abbreviation': False,
            'report_desc': 'Storage Space',
            'placeholder': 'eg. 10GB',
            'verbose_name': 'Storage Space',
        },
        'cyclades.disk': {
            'help_text': ('This is the System Disk that the VMs have that '
                          'run the OS '),
            'help_text_input_each': ("This is the total amount of System Disk "
                                     "that will be granted to each user of "
                                     "this Project (this refers to the total "
                                     "System Disk of all VMs, not each VM's "
                                     "System Disk)  "),
            'is_abbreviation': False,
            'report_desc': 'System Disk',
            'placeholder': 'eg. 5GB, 2GB etc',
            'verbose_name': 'System Disk'
        },
        'cyclades.ram': {
            'help_text': 'RAM used by VMs ',
            'help_text_input_each': ('This is the total amount of RAM that '
                                     'will be granted to each user of this '
                                     'Project (on all VMs)  '),
            'is_abbreviation': True,
            'report_desc': 'RAM',
            'placeholder': 'eg. 4GB',
            'verbose_name': 'ram'
        },
        'cyclades.cpu': {
            'help_text': 'CPUs used by VMs ',
            'help_text_input_each': ('This is the total number of CPUs that '
                                     'will be granted to each user of this '
                                     'Project (on all VMs)  '),
            'is_abbreviation': True,
            'report_desc': 'CPUs',
            'placeholder': 'eg. 1',
            'verbose_name': 'cpu'
        },
        'cyclades.vm': {
            'help_text': ('These are the VMs one can create on the '
                          'Cyclades UI '),
            'help_text_input_each': ('This is the total number of VMs that '
                                     'will be granted to each user of this '
                                     'Project '),
            'is_abbreviation': True,
            'report_desc': 'Virtual Machines',
            'placeholder': 'eg. 2',
            'verbose_name': 'vm',
        },
        'cyclades.network.private': {
            'help_text': ('These are the Private Networks one can create on '
                          'the Cyclades UI. '),
            'help_text_input_each': ('This is the total number of Private '
                                     'Networks that will be granted to each '
                                     'user of this Project '),
            'is_abbreviation': False,
            'report_desc': 'Private Networks',
            'placeholder': 'eg. 1',
            'verbose_name': 'Private Network'
        }
    },
    'groups_order': ['storage', 'compute', 'network'],
    'resources_order': ['pithos+.diskspace',
                        'cyclades.disk',
                        'cyclades.cpu',
                        'cyclades.ram',
                        'cyclades.vm',
                        'cyclades.network.private'
                        ]
}

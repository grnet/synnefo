# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
#
from django.core.management.base import BaseCommand

from synnefo.db.models import (Network, BackendNetwork,
                               BridgePoolTable, MacPrefixPoolTable)
from synnefo.db.pools import EmptyPool


class Command(BaseCommand):
    help = 'Check consistency of unique resources.'

    def handle(self, **options):
        self.detect_bridges()
        self.detect_mac_prefixes()
        self.detect_unique_mac_prefixes()

    def detect_bridges(self):
        write = self.stdout.write

        write("---------------------------------------\n")
        write("Checking consistency of the Bridge Pool\n")
        write("---------------------------------------\n")

        try:
            bridge_pool = BridgePoolTable.get_pool()
        except EmptyPool:
            write("No Bridge Pool\n")
            return
        bridges = []
        for i in xrange(0, bridge_pool.size()):
            if not bridge_pool.is_available(i, index=True) and \
                not bridge_pool.is_reserved(i, index=True):
                    bridges.append(bridge_pool.index_to_value(i))

        write("Used bridges from Pool: %d\n" % len(bridges))

        network_bridges = Network.objects.filter(flavor='PHYSICAL_VLAN',
                                                 deleted=False)\
                                         .values_list('link', flat=True)

        write("Used bridges from Networks: %d\n" % len(network_bridges))

        set_network_bridges = set(network_bridges)
        if len(network_bridges) > len(set_network_bridges):
            write("Found duplicated bridges:\n")
            duplicates = list(network_bridges)
            for bridge in set_network_bridges:
                duplicates.remove(bridge)
            for bridge in set(duplicates):
                write("Duplicated bridge: %s. " % bridge)
                write("Used by the following Networks:\n")
                nets = Network.objects.filter(deleted=False, link=bridge)
                write("  " + "\n  ".join([str(net.id) for net in nets]) + "\n")

    def detect_mac_prefixes(self):
        write = self.stdout.write

        write("---------------------------------------\n")
        write("Checking consistency of the MAC Prefix Pool\n")
        write("---------------------------------------\n")

        try:
            macp_pool = MacPrefixPoolTable.get_pool()
        except EmptyPool:
            write("No mac-prefix pool\n")
            return

        macs = []
        for i in xrange(1, macp_pool.size()):
            if not macp_pool.is_available(i, index=True) and \
               not macp_pool.is_reserved(i, index=True):
                value = macp_pool.index_to_value(i)
                macs.append(value)

        write("Used MAC prefixes from Pool: %d\n" % len(macs))

        network_mac_prefixes = \
            Network.objects.filter(deleted=False, flavor='MAC_FILTERED')\
                           .values_list('mac_prefix', flat=True)
        write("Used MAC prefixes from Networks: %d\n" %
              len(network_mac_prefixes))

        set_network_mac_prefixes = set(network_mac_prefixes)
        if len(network_mac_prefixes) > len(set_network_mac_prefixes):
            write("Found duplicated mac_prefixes:\n")
            duplicates = list(network_mac_prefixes)
            for mac_prefix in set_network_mac_prefixes:
                duplicates.remove(mac_prefix)
            for mac_prefix in set(duplicates):
                write("Duplicated mac_prefix: %s. " % mac_prefix)
                write("Used by the following Networks:\n")
                nets = Network.objects.filter(deleted=False,
                                              mac_prefix=mac_prefix)
                write("  " + "\n  ".join([str(net.id) for net in nets]) + "\n")

    def detect_unique_mac_prefixes(self):
        write = self.stdout.write

        write("---------------------------------------\n")
        write("Checking uniqueness of BackendNetwork prefixes.\n")
        write("---------------------------------------\n")

        back_networks = BackendNetwork.objects
        mac_prefixes = back_networks.filter(deleted=False,
                                            network__flavor='MAC_FILTERED')\
                                    .values_list('mac_prefix', flat=True)
        set_mac_prefixes = set(mac_prefixes)
        if len(mac_prefixes) > len(set_mac_prefixes):
            write("Found duplicated mac_prefixes:\n")
            duplicates = list(mac_prefixes)
            for mac_prefix in set_mac_prefixes:
                duplicates.remove(mac_prefix)
            for mac_prefix in set(duplicates):
                write("Duplicated mac_prefix: %s. " % mac_prefix)
                write("Used by the following BackendNetworks:\n")
                nets = BackendNetwork.objects.filter(deleted=False,
                                                     mac_prefix=mac_prefix)
                write("  " + "\n  ".join([str(net.id) for net in nets]) + "\n")

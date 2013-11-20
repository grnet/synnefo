# Copyright 2013 GRNET S.A. All rights reserved.
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

"""
This is the burnin class that handles stale resources (Servers/Networks)

"""

from synnefo_tools.burnin.common import Proper, SNF_TEST_PREFIX
from synnefo_tools.burnin.cyclades_common import CycladesTests


# Too many public methods. pylint: disable-msg=R0904
class StaleServersTestSuite(CycladesTests):
    """Handle stale Servers"""
    stale_servers = Proper(value=None)

    def test_001_show_stale_servers(self):
        """Show staled servers (servers left from previous runs)"""
        servers = self._get_list_of_servers()
        self.stale_servers = [s for s in servers
                              if s['name'].startswith(SNF_TEST_PREFIX)]

        len_stale = len(self.stale_servers)
        if len_stale == 0:
            self.info("No stale servers found")
            return

        self.info("Found %s stale servers:", len_stale)
        for stl in self.stale_servers:
            self.info("  Server \"%s\" with id %s", stl['name'], stl['id'])

    def test_002_delete_stale_servers(self):
        """Delete staled servers (servers left from previous runs)"""
        len_stale = len(self.stale_servers)
        if not self.delete_stale and len_stale != 0:
            msg = "Use --delete-stale flag to delete stale servers"
            self.error(msg)
            self.fail(msg)
        elif len_stale == 0:
            self.info("No stale servers found")
        else:
            self.info("Deleting %s stale servers:", len_stale)
            for stl in self.stale_servers:
                self.info("  Deleting server \"%s\" with id %s",
                          stl['name'], stl['id'])
                self.clients.cyclades.delete_server(stl['id'])

            for stl in self.stale_servers:
                self._insist_on_server_transition(stl, "ACTIVE", "DELETED")


# Too many public methods. pylint: disable-msg=R0904
class StaleNetworksTestSuite(CycladesTests):
    """Handle stale Networks"""
    def test_001_show_stale_networks(self):
        """Show staled networks (networks left from previous runs)"""
        return

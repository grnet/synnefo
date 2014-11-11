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

"""
This is the burnin class that tests the Snapshots functionality
"""

import random
import stat
import base64

from synnefo_tools.burnin.common import Proper, QPITHOS, QADD, QREMOVE, GB
from synnefo_tools.burnin.cyclades_common import CycladesTests

from kamaki.clients import ClientError


# This class gets replicated into actual TestCases dynamically
class SnapshotsTestSuite(CycladesTests):
    """Test Snapshot functionality"""
    personality = Proper(value=None)
    account = Proper(value=None)
    servers = Proper(value=[])
    snapshot = Proper(value=None)
    tmp_container = Proper(value='burnin-snapshot-temp')
    use_flavor = Proper(value=None)
    personality = Proper(value=None)

    def test_001_submit_create_snapshot(self):
        """Create a server and take a snapshot"""
        self.account = self._get_uuid()
        use_image = random.choice(self._parse_images())
        archipelago_flavors = \
            [f for f in self._parse_flavors() if
             f['SNF:disk_template'].startswith('ext_archipelago')]
        self.assertGreater(len(archipelago_flavors), 0,
                           "No 'archipelago' disk template found")
        self.use_flavor = random.choice(archipelago_flavors)
        if self._image_is(use_image, "linux"):
            # Enforce personality test
            self.info("Creating personality content to be used")
            self.personality = [{
                'path': "/root/test_inj_file",
                'owner': "root",
                'group': "root",
                'mode': stat.S_IRUSR | stat.S_IWUSR,
                'contents': base64.b64encode("This is a personality file")
            }]

        self.info("Using image %s with id %s",
                  use_image['name'], use_image['id'])
        self.info("Using flavor %s with id %s",
                  self.use_flavor['name'], self.use_flavor['id'])
        self.servers.append(self._create_server(use_image,
                                                self.use_flavor,
                                                personality=self.personality,
                                                network=True))
        server = self.servers[0]
        self._insist_on_server_transition(server, ["BUILD"], "ACTIVE")

        volume_id = server['volumes'][0]
        snapshot_name = 'snf-burnin-snapshot_%s' % volume_id
        self.info("Creating snapshot with name '%s', for volume %s",
                  snapshot_name, volume_id)
        self.snapshot = self.clients.block_storage.create_snapshot(
            volume_id, display_name=snapshot_name)
        self.info("Snapshot with id '%s' created", self.snapshot['id'])

        volume_size = self.snapshot['size'] * GB
        self._check_quotas({self.account:
                            [(QPITHOS, QADD, volume_size, None)]})

        self.info('Check that snapshot is listed among snapshots')
        self.assertTrue(self.snapshot['id'] in [i['id'] for i in
                        self.clients.block_storage.list_snapshots()])

        self.info('Get snapshot details')
        self.clients.block_storage.get_snapshot_details(self.snapshot['id'])

        self.info('Check the snapshot is listed under '
                  'pithos snapshots container')
        pithos = self.clients.pithos
        self._set_pithos_account(self.account)
        self.pithos_account = pithos.account
        pithos.container = 'snapshots'
        self.assertTrue(self.snapshot['display_name'] in
                        [o['name'] for o in pithos.list_objects()])

        self._insist_on_snapshot_transition(
            self.snapshot, ["UNAVAILABLE", "CREATING"], "AVAILABLE")

    def test_002_copy_snapshot(self):
        """Copy snapshot to secondary container"""
        self._create_pithos_container(self.tmp_container)
        pithos = self.clients.pithos

        pithos.copy_object(
            src_container=pithos.container,
            src_object=self.snapshot['display_name'],
            dst_container=self.tmp_container,
            dst_object='%s_new' % self.snapshot['display_name'])
        pithos.container = 'snapshots'
        resp1 = pithos.get_object_info(self.snapshot['display_name'])

        pithos.container = self.tmp_container
        resp2 = pithos.get_object_info(
            '%s_new' % self.snapshot['display_name'])

        self.assertEqual(resp1['x-object-hash'], resp2['x-object-hash'])
        self.info('Snapshot has being copied in another container, OK')

        self.info('Check both snapshots are listed among snapshots')
        uploaded_snapshots = [i['id'] for i in
                              self.clients.block_storage.list_snapshots()]
        self.assertTrue(resp1['x-object-uuid'] in uploaded_snapshots)
        self.assertTrue(resp2['x-object-uuid'] in uploaded_snapshots)

        volume_size = self.snapshot['size'] * GB
        self._check_quotas({self.account:
                            [(QPITHOS, QADD, volume_size, None)]})

    def test_003_move_snapshot(self):
        """Move snapshot to secondary container"""
        pithos = self.clients.pithos
        pithos.container = self.tmp_container
        resp1 = pithos.get_object_info(
            '%s_new' % self.snapshot['display_name'])

        pithos.move_object(
            src_container=self.tmp_container,
            src_object='%s_new' % self.snapshot['display_name'],
            dst_container=self.tmp_container,
            dst_object='%s_renamed' % self.snapshot['display_name'])
        self.assertRaises(
            ClientError, pithos.get_object_info,
            '%s_new' % self.snapshot['display_name'])

        resp2 = pithos.get_object_info(
            '%s_renamed' % self.snapshot['display_name'])
        self.info('Snapshot has being renamed, OK')

        self.info('Check both snapshots are listed among snapshots')
        uploaded_snapshots = [i['id'] for i in
                              self.clients.block_storage.list_snapshots()]
        self.assertTrue(self.snapshot['id'] in uploaded_snapshots)
        self.assertEqual(resp1['x-object-uuid'], resp2['x-object-uuid'])
        self.assertTrue(resp2['x-object-uuid'] in uploaded_snapshots)

        # self._check_quotas({self.account: [(QPITHOS, QADD, 0, None)]})
        self._check_quotas({self.account: []})

    def test_004_update_snapshot(self):
        """Update snapshot metadata"""
        pithos = self.clients.pithos
        pithos.container = 'snapshots'
        self.info('Update snapshot \'pithos\' domain metadata')
        pithos.set_object_meta(self.snapshot['display_name'], {'foo': 'bar'})
        resp = pithos.get_object_meta(self.snapshot['display_name'])
        self.assertEqual(resp['x-object-meta-foo'], 'bar')

        self.info('Check snapshot is still listed among snapshots')
        uploaded_snapshots = [i['id'] for i in
                              self.clients.block_storage.list_snapshots()]
        self.assertTrue(self.snapshot['id'] in uploaded_snapshots)

    def test_005_spawn_vm_from_snapshot(self):
        """Spawn a VM from the newly created snapshot"""
        self.servers.append(self._create_server(
            self.snapshot, self.use_flavor,
            network=True))
        server = self.servers[-1]
        self._insist_on_server_transition(server, ["BUILD"], "ACTIVE")

        server = self.clients.cyclades.get_server_details(
            server['id'])
        ipv4 = self._get_ips(server, version=4)
        self.assertTrue(len(ipv4) >= 1)
        self._insist_on_ping(ipv4[0], version=4)

        # use initial server's password
        for inj_file in (self.personality or ()):
            self._check_file_through_ssh(
                ipv4[0], inj_file['owner'], self.servers[0]['adminPass'],
                inj_file['path'], inj_file['contents'])

    def test_006_delete_snapshot(self):
        """Delete snapshot"""
        self.info('Delete snapshot')
        self.clients.block_storage.delete_snapshot(self.snapshot['id'])
        self._insist_on_snapshot_deletion(self.snapshot['id'])

        volume_size = self.snapshot['size'] * GB
        self._check_quotas({self.account:
                            [(QPITHOS, QREMOVE, volume_size, None)]})
        self.snapshot = None

    def test_cleanup(self):
        """Cleanup created servers"""
        for s in self.servers:
            self._disconnect_from_network(s)
        self._delete_servers(self.servers)

    @classmethod
    def tearDownClass(cls):  # noqa
        """Clean up"""
        # Delete snapshot
        snapshots = [s for s in cls.clients.block_storage.list_snapshots()
                     if s['display_name'].startswith("snf-burnin-")]
        for snapshot in snapshots:
            try:
                cls.clients.block_storage.delete_snapshot(snapshot['id'])
            except ClientError:
                pass

        # Delete temp containers
        cls.clients.pithos.account = cls.account
        cls.clients.pithos.container = cls.tmp_container
        try:
            cls.clients.pithos.del_container(delimiter='/')
            cls.clients.pithos.purge_container(cls.tmp_container)
        except ClientError:
            pass

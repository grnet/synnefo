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
This is the burnin class that tests the Pithos functionality

"""

import os
import random
import tempfile
from datetime import datetime

from synnefo_tools.burnin.common import BurninTests, Proper, \
    QPITHOS, QADD, QREMOVE


# pylint: disable=too-many-public-methods
class PithosTestSuite(BurninTests):
    """Test Pithos functionality"""
    containers = Proper(value=None)
    created_container = Proper(value=None)
    now_unformated = Proper(value=datetime.utcnow())

    def test_005_account_head(self):
        """HEAD on pithos account"""
        self._set_pithos_account(self._get_uuid())
        pithos = self.clients.pithos
        resp = pithos.account_head()
        self.assertEqual(resp.status_code, 204)
        self.info('Returns 204')

        resp = pithos.account_head(until='1000000000')
        self.assertEqual(resp.status_code, 204)
        datestring = unicode(resp.headers['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        self.assertTrue(any([
            h.startswith('x-account-policy-quota') for h in resp.headers]))
        self.info('Until and account policy quota exist')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.account_head(
                if_modified_since=now_formated, success=(204, 304, 412))
            resp2 = pithos.account_head(
                if_unmodified_since=now_formated, success=(204, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)
        self.info('If_(un)modified_since is OK')

    def test_010_account_get(self):  # pylint: disable=too-many-locals
        """Test account_get"""
        self.info('Preparation')
        pithos = self.clients.pithos
        for i in range(1, 3):
            cont_name = "cont%s_%s%s" % (
                i, self.run_id, random.randint(1000, 9999))
            self._create_pithos_container(cont_name)
        pithos.container, obj = cont_name, 'shared_file'
        pithos.create_object(obj)
        pithos.set_object_sharing(obj, read_permission='*')
        self.info('Created object /%s/%s' % (cont_name, obj))

        resp = pithos.list_containers()
        full_len = len(resp)
        self.assertTrue(full_len > 2)
        self.info('Normal use is OK')

        resp = pithos.account_get(limit=1)
        self.assertEqual(len(resp.json), 1)
        self.info('Limit works')

        resp = pithos.account_get(marker='cont')
        cont1, cont3 = resp.json[0], resp.json[2]
        self.info('Marker works')

        resp = pithos.account_get(limit=2, marker='cont')
        conames = [container['name'] for container in resp.json if (
            container['name'].lower().startswith('cont'))]
        self.assertTrue(cont1['name'] in conames)
        self.assertFalse(cont3['name'] in conames)
        self.info('Marker-limit combination works')

        resp = pithos.account_get(show_only_shared=True)
        self.assertTrue(cont_name in [c['name'] for c in resp.json])
        self.info('Show-only-shared works')

        resp = pithos.account_get(until=1342609206.0)
        self.assertTrue(len(resp.json) <= full_len)
        self.info('Until works')

        for date_format in pithos.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(date_format)
            resp1 = pithos.account_get(
                if_modified_since=now_formated, success=(200, 304, 412))
            resp2 = pithos.account_get(
                if_unmodified_since=now_formated, success=(200, 304, 412))
            self.assertNotEqual(resp1.status_code, resp2.status_code)
        self.info('If_(un)modified_since is OK')

    def test_051_list_containers(self):
        """Test container list actually returns containers"""
        # self.assertTrue(False)   # This is a stoper!
        self.containers = self._get_list_of_containers()
        self.assertGreater(len(self.containers), 0)

    def test_052_unique_containers(self):
        """Test if containers have unique names"""
        names = [n['name'] for n in self.containers]
        names = sorted(names)
        self.assertEqual(sorted(list(set(names))), names)

    def test_053_create_container(self):
        """Test creating a new container"""
        names = [n['name'] for n in self.containers]
        while True:
            rand_num = random.randint(1000, 9999)
            rand_name = "%s%s" % (self.run_id, rand_num)
            self.info("Trying container name %s", rand_name)
            if rand_name not in names:
                break
            self.info("Container name %s already exists", rand_name)
        # Create container
        self._create_pithos_container(rand_name)
        # Verify that container is created
        containers = self._get_list_of_containers()
        self.info("Verify that container %s is created", rand_name)
        names = [n['name'] for n in containers]
        self.assertIn(rand_name, names)
        # Keep the name of the container so we can remove it
        # at cleanup phase, if something goes wrong.
        self.created_container = rand_name

    def test_054_upload_file(self):
        """Test uploading a txt file to Pithos"""
        # Create a tmp file
        with tempfile.TemporaryFile(dir=self.temp_directory) as fout:
            fout.write("This is a temp file")
            fout.seek(0, 0)
            # Upload the file,
            # The container is the one choosen during the `create_container'
            self.clients.pithos.upload_object("test.txt", fout)
            # Verify quotas
            size = os.fstat(fout.fileno()).st_size
            changes = \
                {self._get_uuid(): [(QPITHOS, QADD, size, None)]}
            self._check_quotas(changes)

    def test_055_download_file(self):
        """Test downloading the file from Pithos"""
        # Create a tmp directory to save the file
        with tempfile.TemporaryFile(dir=self.temp_directory) as fout:
            self.clients.pithos.download_object("test.txt", fout)
            # Now read the file
            fout.seek(0, 0)
            contents = fout.read()
            # Compare results
            self.info("Comparing contents with the uploaded file")
            self.assertEqual(contents, "This is a temp file")

    def test_056_remove(self):
        """Test removing files and containers from Pithos"""
        self.info("Removing the file %s from container %s",
                  "test.txt", self.created_container)
        # The container is the one choosen during the `create_container'
        content_length = \
            self.clients.pithos.get_object_info("test.txt")['content-length']
        self.clients.pithos.del_object("test.txt")

        # Verify quotas
        changes = \
            {self._get_uuid(): [(QPITHOS, QREMOVE, content_length, None)]}
        self._check_quotas(changes)

        self.info("Removing the container %s", self.created_container)
        self.clients.pithos.purge_container()

        # List containers
        containers = self._get_list_of_containers()
        self.info("Check that the container %s has been deleted",
                  self.created_container)
        names = [n['name'] for n in containers]
        self.assertNotIn(self.created_container, names)
        # We successfully deleted our container, no need to do it
        # in our clean up phase
        self.created_container = None

    @classmethod
    def tearDownClass(cls):  # noqa
        """Clean up"""
        if cls.created_container is not None:
            cls.clients.pithos.del_container(delimiter='/')
            cls.clients.pithos.purge_container()

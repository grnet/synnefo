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
This is the burnin class that tests the Pithos functionality

"""

import os
import random
import tempfile

from synnefo_tools.burnin.common import BurninTests, Proper


# pylint: disable=too-many-public-methods
class PithosTestSuite(BurninTests):
    """Test Pithos functionality"""
    containers = Proper(value=None)
    created_container = Proper(value=None)

    def test_001_list_containers(self):
        """Test container list actually returns containers"""
        self._set_pithos_account(self._get_uuid())
        self.containers = self._get_list_of_containers()
        self.assertGreater(len(self.containers), 0)

    def test_002_unique_containers(self):
        """Test if containers have unique names"""
        names = [n['name'] for n in self.containers]
        names = sorted(names)
        self.assertEqual(sorted(list(set(names))), names)

    def test_003_create_container(self):
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

    def test_004_upload_file(self):
        """Test uploading a txt file to Pithos"""
        # Create a tmp file
        with tempfile.TemporaryFile(dir=self.temp_directory) as fout:
            fout.write("This is a temp file")
            fout.seek(0, 0)
            # Upload the file,
            # The container is the one choosen during the `create_container'
            self.clients.pithos.upload_object("test.txt", fout)
            # Verify quotas
            self._check_quotas(diskspace=+os.fstat(fout.fileno()).st_size)

    def test_005_download_file(self):
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

    def test_006_remove(self):
        """Test removing files and containers from Pithos"""
        self.info("Removing the file %s from container %s",
                  "test.txt", self.created_container)
        # The container is the one choosen during the `create_container'
        content_length = \
            self.clients.pithos.get_object_info("test.txt")['content-length']
        self.clients.pithos.del_object("test.txt")

        # Verify quotas
        self._check_quotas(diskspace=-int(content_length))

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


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
This is the burnin class that tests the Flavors/Images functionality

"""

import os
import shutil

from kamaki.clients import ClientError

from synnefo_tools.burnin.common import BurninTests, Proper


# Too many public methods. pylint: disable-msg=R0904
class FlavorsTestSuite(BurninTests):
    """Test flavor lists for consistency"""
    simple_flavors = Proper(value=None)
    detailed_flavors = Proper(value=None)
    simple_names = Proper(value=None)

    def test_001_simple_flavors(self):
        """Test flavor list actually returns flavors"""
        self.simple_flavors = self._get_list_of_flavors(detail=False)
        self.assertGreater(len(self.simple_flavors), 0)

    def test_002_get_detailed_flavors(self):
        """Test detailed flavor list is the same length as list"""
        self.detailed_flavors = self._get_list_of_flavors(detail=True)
        self.assertEquals(len(self.simple_flavors), len(self.detailed_flavors))

    def test_003_same_flavor_names(self):
        """Test detailed and simple flavor list contain same names"""
        names = sorted([flv['name'] for flv in self.simple_flavors])
        self.simple_names = names
        detailed_names = sorted([flv['name'] for flv in self.detailed_flavors])
        self.assertEqual(self.simple_names, detailed_names)

    def test_004_unique_flavor_names(self):
        """Test flavors have unique names"""
        self.assertEqual(sorted(list(set(self.simple_names))),
                         self.simple_names)

    def test_005_well_formed_names(self):
        """Test flavors have well formed names

        Test flavors have names of the form CxxRyyDzz, where xx is vCPU count,
        yy is RAM in MiB, zz is Disk in GiB

        """
        for flv in self.detailed_flavors:
            flavor = (flv['vcpus'], flv['ram'], flv['disk'],
                      flv['SNF:disk_template'])
            self.assertEqual("C%dR%dD%d%s" % flavor, flv['name'],
                             "Flavor %s doesn't match its specs" % flv['name'])


# --------------------------------------------------------------------
# Too many public methods. pylint: disable-msg=R0904
class ImagesTestSuite(BurninTests):
    """Test image lists for consistency"""
    simple_images = Proper(value=None)
    detailed_images = Proper(value=None)
    system_images = Proper(value=None)
    temp_dir = Proper(value=None)
    temp_image_name = Proper(value=None)
    temp_image_file = Proper(value=None)

    def test_001_list_images(self):
        """Test simple image list actually returns images"""
        self.simple_images = self._get_list_of_images(detail=False)
        self.assertGreater(len(self.simple_images), 0)

    def test_002_list_images_detailed(self):
        """Test detailed image list is the same length as simple list"""
        self.detailed_images = self._get_list_of_images(detail=True)
        self.assertEqual(len(self.simple_images), len(self.detailed_images))

    def test_003_same_image_names(self):
        """Test detailed and simple image list contain the same names"""
        snames = sorted([i['name'] for i in self.simple_images])
        dnames = sorted([i['name'] for i in self.detailed_images])
        self.assertEqual(snames, dnames)

    def test_004_system_images(self):
        """Test that there are system images registered"""
        images = self._get_list_of_sys_images(images=self.detailed_images)
        self.system_images = images
        self.assertGreater(len(images), 0)

    def test_005_unique_image_names(self):
        """Test system images have unique names"""
        names = sorted([i['name'] for i in self.system_images])
        self.assertEqual(sorted(list(set(names))), names)

    def test_006_image_metadata(self):
        """Test every system image has specific metadata defined"""
        keys = frozenset(["osfamily", "root_partition"])
        for i in self.system_images:
            self.assertTrue(keys.issubset(i['properties'].keys()))

    def test_007_download_image(self):
        """Download image from Pithos"""
        # Find the 'Debian Base' image
        images = self._find_images(["name:^Debian Base$"],
                                   images=self.system_images)
        image = images[0]
        self.info("Will use %s with id %s", image['name'], image['id'])
        image_location = \
            image['location'].replace("://", " ").replace("/", " ").split()
        image_owner = image_location[1]
        self.info("Image's owner is %s", image_owner)
        image_container = image_location[2]
        self.info("Image's container is %s", image_container)
        image_name = image_location[3]
        self.info("Image's name is %s", image_name)
        self.temp_image_name = image_name

        self._set_pithos_account(image_owner)
        self._set_pithos_container(image_container)

        # Create temp directory
        self.temp_dir = self._create_tmp_directory()
        self.temp_image_file = \
            os.path.join(self.temp_dir, self.temp_image_name)

        # Write to file
        self.info("Downloading image to %s", self.temp_image_file)
        with open(self.temp_image_file, "w+b") as fout:
            self.clients.pithos.download_object(image_name, fout)

    def test_008_upload_image(self):
        """Upload the image to Pithos"""
        self._set_pithos_account(self._get_uuid())
        self._create_pithos_container("burnin-images")
        with open(self.temp_image_file, "r+b") as fin:
            self.clients.pithos.upload_object(self.temp_image_name, fin)

    def test_009_register_image(self):
        """Register image to Plankton"""
        location = "pithos://" + self._get_uuid() + \
            "/burnin-images/" + self.temp_image_name
        self.info("Registering image %s", location)

        params = {'is_public': False}
        properties = {'OSFAMILY': "linux", 'ROOT_PARTITION': 1}
        self.clients.image.register(self.temp_image_name, location,
                                    params, properties)

        # Check that image is registered
        self.info("Checking that image has been registered")
        images = self._get_list_of_images(detail=True)
        images = [i for i in images if i['location'] == location]
        self.assertEqual(len(images), 1)
        self.info("Image registered with id %s", images[0]['id'])

    def test_010_cleanup_image(self):
        """Remove uploaded image from Pithos"""
        # Remove uploaded image
        self.info("Deleting uploaded image %s", self.temp_image_name)
        self.clients.pithos.del_object(self.temp_image_name)
        self.temp_image_name = None
        # Remove temp directory
        self.info("Deleting temp directory %s", self.temp_dir)
        self._remove_tmp_directory(self.temp_dir)
        self.temp_dir = None

    @classmethod
    def tearDownClass(cls):  # noqa
        """Clean up"""
        if cls.temp_image_name is not None:
            try:
                cls.clients.pithos.del_object(cls.temp_image_name)
            except ClientError:
                pass

        if cls.temp_dir is not None:
            try:
                shutil.rmtree(cls.temp_dir)
            except OSError:
                pass

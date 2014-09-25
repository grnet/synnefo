
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
This is the burnin class that tests the Flavors/Images functionality

"""

import os
import shutil

from kamaki.clients import ClientError

from synnefo_tools.burnin.common import BurninTests, Proper, \
    QPITHOS, QADD, QREMOVE


# pylint: disable=too-many-public-methods
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
# pylint: disable=too-many-public-methods
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
        self._set_pithos_container("burnin-images")
        file_size = os.path.getsize(self.temp_image_file)
        with open(self.temp_image_file, "r+b") as fin:
            self.clients.pithos.upload_object(self.temp_image_name, fin)

        # Verify quotas
        changes = \
            {self._get_uuid(): [(QPITHOS, QADD, file_size, None)]}
        self._check_quotas(changes)

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

        self.info("Registering with unicode name")
        uni_str = u'\u03b5\u03b9\u03ba\u03cc\u03bd\u03b1'
        uni_name = u'%s, or %s in Greek' % (self.temp_image_name, uni_str)
        img = self.clients.image.register(
            uni_name, location, params, properties)

        self.info('Checking if image with unicode name exists')
        found_img = self.clients.image.get_meta(img['id'])
        self.assertEqual(found_img['name'], uni_name)
        self.info("Image registered with id %s", found_img['id'])

        self.info("Checking if image is listed "
                  "under the specific container in pithos")
        self._set_pithos_account(self._get_uuid())
        pithos = self.clients.pithos
        pithos.container = 'burnin-images'
        self.assertTrue(self.temp_image_name in (
            o['name'] for o in pithos.list_objects()))

        self.info("Checking copying image to "
                  "another pithos container.")
        pithos.container = other_container = 'burnin-images-backup'
        pithos.create_container()
        pithos.copy_object(
            src_container='burnin-images',
            src_object=self.temp_image_name,
            dst_container=other_container,
            dst_object='%s_copy' % self.temp_image_name)

        # Verify quotas
        file_size = os.path.getsize(self.temp_image_file)
        changes = \
            {self._get_uuid(): [(QPITHOS, QADD, file_size, None)]}
        self._check_quotas(changes)

        self.info("Checking copied image "
                  "is listed among the images.")
        images = self._get_list_of_images(detail=True)
        locations = [i['location'] for i in images]
        location2 = "pithos://" + self._get_uuid() + \
            "/burnin-images-backup/" + '%s_copy' % self.temp_image_name
        self.assertTrue(location2 in locations)

        self.info("Set image metadata in the pithos domain")
        pithos.set_object_meta('%s_copy' % self.temp_image_name,
                {'foo': 'bar'})

        self.info("Checking copied image "
                  "is still listed among the images.")
        images = self._get_list_of_images(detail=True)
        locations = [i['location'] for i in images]
        location2 = "pithos://" + self._get_uuid() + \
            "/burnin-images-backup/" + '%s_copy' % self.temp_image_name
        self.assertTrue(location2 in locations)

        # delete copied object
        self.clients.pithos.del_object('%s_copy' % self.temp_image_name)

        # Verify quotas
        file_size = os.path.getsize(self.temp_image_file)
        changes = \
            {self._get_uuid(): [(QPITHOS, QREMOVE, file_size, None)]}
        self._check_quotas(changes)

    def test_010_cleanup_image(self):
        """Remove uploaded image from Pithos"""
        # Remove uploaded image
        self.info("Deleting uploaded image %s", self.temp_image_name)
        self._set_pithos_container("burnin-images")
        self.clients.pithos.del_object(self.temp_image_name)
        # Verify quotas
        file_size = os.path.getsize(self.temp_image_file)
        changes = \
            {self._get_uuid(): [(QPITHOS, QREMOVE, file_size, None)]}
        self._check_quotas(changes)
        self.temp_image_name = None
        # Remove temp directory
        self.info("Deleting temp directory %s", self.temp_dir)
        self._remove_tmp_directory(self.temp_dir)
        self.temp_dir = None

    @classmethod
    def tearDownClass(cls):  # noqa
        """Clean up"""
        for container in ["burnin-images", "burnin-images-backup"]:
            cls.clients.pithos.container = container
            try:
                cls.clients.pithos.del_container(delimiter='/')
                cls.clients.pithos.purge_container(container)
            except ClientError:
                pass

        if cls.temp_dir is not None:
            try:
                shutil.rmtree(cls.temp_dir)
            except OSError:
                pass

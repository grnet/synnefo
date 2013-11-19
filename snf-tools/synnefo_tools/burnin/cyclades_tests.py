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
This is the burnin class that tests the Cyclades functionality

"""

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

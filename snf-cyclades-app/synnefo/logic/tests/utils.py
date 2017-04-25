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

from django.test import TestCase

from synnefo.logic import utils
from django.conf import settings
from synnefo.db.models import VirtualMachine, Network
from synnefo.db.models_factory import VirtualMachineFactory


class NameConversionTest(TestCase):
    def setUp(self):
        settings.BACKEND_PREFIX_ID = 'snf-'

    def test_id_from_iname(self):
        self.assertEqual(utils.id_from_instance_name('snf-42'), 42)
        for name in [None, 'foo', 'snf42', 'snf-a', 'snf-snf-42', 1234]:
            self.assertRaises(VirtualMachine.InvalidBackendIdError,
                              utils.id_from_instance_name, '')

    def test_iname_from_id(self):
        self.assertEqual(utils.id_to_instance_name(42), 'snf-42')

    def test_id_from_net_name(self):
        self.assertEqual(utils.id_from_network_name('snf-net-42'), 42)
        for name in [None, 'foo', 'snf42', 'snf-net-a', 'snf-snf-42', 1234]:
            self.assertRaises(Network.InvalidBackendIdError,
                              utils.id_from_network_name, '')

    def test_net_name_from_id(self):
            self.assertEqual(utils.id_to_network_name(42), 'snf-net-42')


class APIStateTest(TestCase):
    def test_correct_state(self):
        vm = VirtualMachineFactory()
        vm.operstate = 'foo'
        self.assertEqual(utils.get_rsapi_state(vm), "UNKNOWN")
        vm.operstate = "STARTED"
        vm.deleted = True
        self.assertEqual(utils.get_rsapi_state(vm), "DELETED")
        vm.deleted = False
        vm.backendopcode = "OP_INSTANCE_REBOOT"
        vm.backendjobstatus = "waiting"
        self.assertEqual(utils.get_rsapi_state(vm), "REBOOT")


class HidePass(TestCase):
    def test_no_osparams(self):
        foo = {'foo': 'bar'}
        self.assertTrue(foo is utils.hide_pass(foo))
        foo = {'osparams': {}, 'bar': 'foo'}
        self.assertTrue(foo is utils.hide_pass(foo))

    def test_hidden_pass(self):
        foo = {'osparams': {'img_passwd': 'pass'}, 'bar': 'foo'}
        after = {'osparams': {'img_passwd': 'xxxxxxxx'}, 'bar': 'foo'}
        self.assertEqual(after, utils.hide_pass(foo))

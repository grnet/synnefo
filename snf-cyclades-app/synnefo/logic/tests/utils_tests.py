# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

# vim: set fileencoding=utf-8 :
# Copyright 2013 GRNET S.A. All rights reserved.
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

# Provides automated tests for logic module
from django.test import TestCase
#from snf_django.utils.testing import mocked_quotaholder
from synnefo.logic import servers
from synnefo.db import models_factory as mfactory
from mock import patch


@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class ServerTest(TestCase):
    def test_connect_network(self, mrapi):
        # Common connect
        net = mfactory.NetworkFactory(subnet="192.168.2.0/24",
                                      gateway="192.168.2.1",
                                      state="ACTIVE",
                                      dhcp=True,
                                      flavor="CUSTOM")
        vm = mfactory.VirtualMachineFactory()
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
        mrapi().ModifyInstance.return_value = 42
        servers.connect(vm, net)
        pool = net.get_pool(with_lock=False)
        self.assertFalse(pool.is_available("192.168.2.2"))
        args, kwargs = mrapi().ModifyInstance.call_args
        nics = kwargs["nics"][0]
        self.assertEqual(args[0], vm.backend_vm_id)
        self.assertEqual(nics[0], "add")
        self.assertEqual(nics[1]["ip"], "192.168.2.2")
        self.assertEqual(nics[1]["network"], net.backend_id)

        # No dhcp
        vm = mfactory.VirtualMachineFactory()
        net = mfactory.NetworkFactory(subnet="192.168.2.0/24",
                                      gateway="192.168.2.1",
                                      state="ACTIVE",
                                      dhcp=False)
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
        servers.connect(vm, net)
        pool = net.get_pool(with_lock=False)
        self.assertTrue(pool.is_available("192.168.2.2"))
        args, kwargs = mrapi().ModifyInstance.call_args
        nics = kwargs["nics"][0]
        self.assertEqual(args[0], vm.backend_vm_id)
        self.assertEqual(nics[0], "add")
        self.assertEqual(nics[1]["ip"], None)
        self.assertEqual(nics[1]["network"], net.backend_id)

        # Test connect to IPv6 only network
        vm = mfactory.VirtualMachineFactory()
        net = mfactory.NetworkFactory(subnet6="2000::/64",
                                      state="ACTIVE",
                                      gateway="2000::1")
        mfactory.BackendNetworkFactory(network=net, backend=vm.backend)
        servers.connect(vm, net)
        args, kwargs = mrapi().ModifyInstance.call_args
        nics = kwargs["nics"][0]
        self.assertEqual(args[0], vm.backend_vm_id)
        self.assertEqual(nics[0], "add")
        self.assertEqual(nics[1]["ip"], None)
        self.assertEqual(nics[1]["network"], net.backend_id)

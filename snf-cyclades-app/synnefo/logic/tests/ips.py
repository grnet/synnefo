# vim: set fileencoding=utf-8 :
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

# Provides automated tests for logic module
from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from snf_django.lib.api import faults
from snf_django.utils.testing import mocked_quotaholder
from synnefo.logic import ips
from synnefo.db import models_factory as mfactory
from synnefo.db.models import IPAddress


class IPTest(TestCase):

    """Test suite for actions on IP addresses."""

    def setUp(self):
        """Common setup method for this suite.

        This setUp method creates a simple IP Pool from which IPs can be
        created.
        """
        self.subnet = mfactory.IPv4SubnetFactory(network__floating_ip_pool=True)
        self.network = self.subnet.network

    def test_create(self):
        """Test if a floating IP is created properly."""
        with mocked_quotaholder():
            ip = ips.create_floating_ip("1134", network=self.network)
        self.assertEqual(len(self.network.ips.all()), 1)
        self.assertEqual(self.network.ips.all()[0], ip)

    def test_delete(self):
        """Test if the delete action succeeds/fails properly."""
        # Create a floating IP and force-attach it to a NIC instance.
        vm = mfactory.VirtualMachineFactory()
        nic = mfactory.NetworkInterfaceFactory(network=self.network,
                                               machine=vm)
        with mocked_quotaholder():
            ip = ips.create_floating_ip("1134", network=self.network)
        ip.nic = nic

        # Test 1 - Check if we can delete an IP attached to a VM.
        #
        # The validate function and the action should both fail with the
        # following message.
        expected_msg = "IP '{}' is used by server '{}'".format(ip.id, vm.id)

        # Verify that the validate function fails in silent mode.
        res, msg = ips.validate_ip_action(ip, "DELETE", silent=True)
        self.assertFalse(res)
        self.assertEqual(msg, expected_msg)

        # Verify that the validate function fails in non-silent mode.
        with self.assertRaises(faults.Conflict) as cm:
            ips.validate_ip_action(ip, "DELETE", silent=False)
        self.assertEqual(cm.exception.message, expected_msg)

        # Verify that the delete action fails with exception.
        with mocked_quotaholder():
            with self.assertRaises(faults.Conflict) as cm:
                ips.delete_floating_ip(ip)
        self.assertEqual(cm.exception.message, expected_msg)

        # Test 2 - Check if we can delete a free IP.
        #
        # Force-detach IP from NIC.
        ip.nic = None

        # Verify that the validate function passes in silent mode.
        res, _ = ips.validate_ip_action(ip, "DELETE", silent=True)
        self.assertTrue(res)

        # Verify that the delete action succeeds.
        with mocked_quotaholder():
            ips.delete_floating_ip(ip)
        with self.assertRaises(ObjectDoesNotExist):
            IPAddress.objects.get(id=ip.id)

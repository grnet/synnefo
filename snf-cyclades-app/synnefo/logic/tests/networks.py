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
from snf_django.lib.api import faults
from snf_django.utils.testing import mocked_quotaholder
from synnefo.logic import networks
from synnefo.db import models_factory as mfactory
from synnefo.db.models import BridgePoolTable, MacPrefixPoolTable
from synnefo import settings
from copy import copy


#@patch("synnefo.logic.rapi_pool.GanetiRapiClient")
class NetworkTest(TestCase):
    def test_create(self):
        kwargs = {
            "name": "test",
            "userid": "user",
            "flavor": "CUSTOM",
        }
        # wrong flavor
        kw = copy(kwargs)
        kw["flavor"] = "UNKNOWN"
        self.assertRaises(faults.BadRequest, networks.create, **kw)
        # Test create objet
        kwargs["public"] = True
        with mocked_quotaholder():
            net = networks.create(**kwargs)
        self.assertEqual(net.public, True)
        self.assertEqual(net.flavor, "CUSTOM")
        self.assertEqual(net.action, "CREATE")
        self.assertEqual(net.state, "ACTIVE")
        self.assertEqual(net.name, "test")
        self.assertEqual(net.userid, "user")

        # Test for each for flavor type
        # MAC_FILTERED
        kwargs["flavor"] = "MAC_FILTERED"
        # Test exception if no rules exists
        self.assertRaises(faults.ServiceUnavailable, networks.create, **kwargs)
        mfactory.MacPrefixPoolTableFactory(base="aa:bb:0")
        with mocked_quotaholder():
                net = networks.create(**kwargs)
        self.assertEqual(net.mode, "bridged")
        self.assertEqual(net.mac_prefix, "aa:bb:1")
        self.assertEqual(net.link, settings.DEFAULT_MAC_FILTERED_BRIDGE)
        self.assertEqual(net.backend_tag, ["private-filtered"])
        pool = MacPrefixPoolTable.get_pool()
        self.assertFalse(pool.is_available("aa:bb:1"))

        # PHYSICAL_VLAN
        kwargs["flavor"] = "PHYSICAL_VLAN"
        # Test exception if no rules exists
        self.assertRaises(faults.ServiceUnavailable, networks.create, **kwargs)
        mfactory.BridgePoolTableFactory(base="prv")
        with mocked_quotaholder():
            net = networks.create(**kwargs)
        self.assertEqual(net.mode, "bridged")
        self.assertEqual(net.mac_prefix, settings.DEFAULT_MAC_PREFIX)
        self.assertEqual(net.link, "prv1")
        self.assertEqual(net.backend_tag, ["physical-vlan"])
        pool = BridgePoolTable.get_pool()
        self.assertFalse(pool.is_available(net.link))

        # IP_LESS_ROUTED
        kwargs["flavor"] = "IP_LESS_ROUTED"
        with mocked_quotaholder():
            net = networks.create(**kwargs)
        self.assertEqual(net.mode, "routed")
        self.assertEqual(net.mac_prefix, settings.DEFAULT_MAC_PREFIX)
        self.assertEqual(net.link, "%slink-%d" % (settings.BACKEND_PREFIX_ID,
                                                  net.id))
        self.assertEqual(net.backend_tag, ["ip-less-routed"])

        # CUSTOM
        kwargs["flavor"] = "CUSTOM"
        with mocked_quotaholder():
            net = networks.create(**kwargs)
        self.assertEqual(net.mode, "bridged")
        self.assertEqual(net.mac_prefix, settings.DEFAULT_MAC_PREFIX)
        self.assertEqual(net.link, settings.DEFAULT_BRIDGE)
        self.assertEqual(net.backend_tag, [])

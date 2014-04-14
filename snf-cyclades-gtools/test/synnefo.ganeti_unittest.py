#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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
#

import sys
import logging
from synnefo.ganeti.eventd import get_instance_nics
from mock import patch

log = logging.getLogger()

# Use backported unittest functionality if Python < 2.7
try:
    import unittest2 as unittest
except ImportError:
    if sys.version_info < (2, 7):
        raise Exception("The unittest2 package is required for Python < 2.7")
    import unittest


@patch("ganeti.cli.GetClient")
class GanetiNICTestCase(unittest.TestCase):
    def test_no_nics(self, client):
        ret = [[[], [], [], [], [], []]]
        client.return_value.QueryInstances.return_value = ret
        self.assertEqual(get_instance_nics('test', log), [])

    def test_one_nic(self, client):
        ret = [[["network"], ["ip"], ["mac"], ["mode"], ["link"],
                ["tag1", "tag2"]]]
        client.return_value.QueryInstances.return_value = ret
        nics0 = get_instance_nics("test", log)
        nics1 = [{"network": "network",
                  "ip": "ip",
                  "mac": "mac",
                  "mode": "mode",
                  "link": "link"}]
        self.assertEqual(nics0, nics1)

    def test_two_nics(self, client):
        ret = [[["network1", "network2"], ["ip1", "ip2"], ["mac1", "mac2"],
                ["mode1", "mode2"], ["link1", "link2"], ["tag1", "tag2"]]]
        client.return_value.QueryInstances.return_value = ret
        nics0 = get_instance_nics("test", log)
        nics1 = [{"network": "network1",
                  "ip": "ip1",
                  "mac": "mac1",
                  "mode": "mode1",
                  "link": "link1"},
                  {"network": "network2",
                   "ip": "ip2",
                   "mac": "mac2",
                   "mode": "mode2",
                   "link": "link2"}]
        self.assertEqual(nics0, nics1)

    def test_firewall(self, client):
        ret = [[["network"], ["ip"], ["mac"], ["mode"], ["link"],
            ["tag1", "synnefo:network:0:protected"]]]
        client.return_value.QueryInstances.return_value = ret
        nics0 = get_instance_nics("test", log)
        nics1 = [{"network": "network",
                  "ip": "ip",
                  "mac": "mac",
                  "mode": "mode",
                  "link": "link",
                  "firewall": "protected"}]
        self.assertEqual(nics0, nics1)


if __name__ == '__main__':
    unittest.main()

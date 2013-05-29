#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

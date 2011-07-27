#!/usr/bin/env python
#
# -*- coding: utf-8 -*-
#
# Copyright 2011 GRNET S.A. All rights reserved.
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
#

"""Unit Tests for the Ganeti-specific interfaces in synnefo.ganeti

Provides unit tests for the code implementing
the Ganeti notification daemon and the Ganeti hook in Synnefo.

"""

# This assumes a test-specific configuration file
# is in the same directory as the unit test script
import os
os.environ["SYNNEFO_CONFIG_DIR"] = os.path.dirname(__file__)

import logging
import unittest

from synnefo.ganeti.hook import ganeti_net_status


class GanetiHookTestCase(unittest.TestCase):

    def setUp(self):
        # Example Ganeti environment, based on from
        # http://docs.ganeti.org/ganeti/master/html/hooks.html?highlight=hooks#examples
        self.env = {
            'GANETI_CLUSTER': 'cluster1.example.com',
            'GANETI_DATA_DIR': '/var/lib/ganeti',
            'GANETI_FORCE': 'False',
            'GANETI_HOOKS_PATH': 'instance-start',
            'GANETI_HOOKS_PHASE': 'post',
            'GANETI_HOOKS_VERSION': '2',
            'GANETI_INSTANCE_DISK0_MODE': 'rw',
            'GANETI_INSTANCE_DISK0_SIZE': '128',
            'GANETI_INSTANCE_DISK_COUNT': '1',
            'GANETI_INSTANCE_DISK_TEMPLATE': 'drbd',
            'GANETI_INSTANCE_MEMORY': '128',
            'GANETI_INSTANCE_TAGS': 'tag1 synnefo:network:0:protected tag2',
            'GANETI_INSTANCE_NAME': 'instance2.example.com',
            'GANETI_INSTANCE_NIC0_BRIDGE': 'xen-br0',
            'GANETI_INSTANCE_NIC0_IP': '147.102.3.1',
            'GANETI_INSTANCE_NIC0_MAC': '00:01:de:ad:be:ef',
            'GANETI_INSTANCE_NIC1_MAC': '00:01:de:ad:ba:be',
            'GANETI_INSTANCE_NIC2_MAC': '00:01:02:03:04:05',
            'GANETI_INSTANCE_NIC2_IP': '147.102.3.98',
            'GANETI_INSTANCE_NIC_COUNT': '3',
            'GANETI_INSTANCE_OS_TYPE': 'debootstrap',
            'GANETI_INSTANCE_PRIMARY': 'node3.example.com',
            'GANETI_INSTANCE_SECONDARY': 'node5.example.com',
            'GANETI_INSTANCE_STATUS': 'down',
            'GANETI_INSTANCE_VCPUS': '1',
            'GANETI_MASTER': 'node1.example.com',
            'GANETI_OBJECT_TYPE': 'INSTANCE',
            'GANETI_OP_CODE': 'OP_INSTANCE_STARTUP',
            'GANETI_OP_TARGET': 'instance2.example.com'
        }

    def test_ganeti_net_status(self):
        e = self.env
        expected = {
            'type': 'ganeti-net-status',
            'instance': 'instance2.example.com',
            'nics': [
                {
                    'ip': '147.102.3.1', 'mac': '00:01:de:ad:be:ef',
                    'link': 'xen-br0', 'ipv6': '2001:db8::201:deff:fead:beef',
                    'firewall': 'protected'
                },
                { 'mac': '00:01:de:ad:ba:be' },
                { 'ip': '147.102.3.98', 'mac': '00:01:02:03:04:05' }
            ]
        }

        self.assertEqual(ganeti_net_status(logging, e), expected)


if __name__ == '__main__':
    unittest.main()


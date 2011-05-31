#
# Unit Tests for the Ganeti-specific interfaces
#
# Provides unit tests for the code implementing
# the Ganeti notification daemon and the Ganeti hook in Synnefo.
#
# Copyright 2011 Greek Research and Technology Network
#
import logging

from django.test import TestCase
from django.conf import settings

from ganeti.hooks import ganeti_net_status

class GanetiHookTestCase(TestCase):
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
                { 'ip': '147.102.3.1', 'mac': '00:01:de:ad:be:ef', 'link': 'xen-br0' },
                { 'mac': '00:01:de:ad:ba:be' },
                { 'ip': '147.102.3.98', 'mac': '00:01:02:03:04:05' }
            ]
        }

        self.assertEqual(ganeti_net_status(logging, e), expected)

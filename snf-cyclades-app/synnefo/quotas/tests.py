#!/usr/bin/env python
#
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
#
from mock import patch
from django.test import TestCase
from synnefo.db import models_factory as mfactory

from synnefo import quotas
from synnefo.quotas import util


class GetDBHoldingsTestCase(TestCase):
    maxDiff = None

    def test_no_holdings(self):
        holdings = util.get_db_holdings(user=None)
        self.assertEqual(holdings, {})

    def test_vm_holdings(self):
        flavor = mfactory.FlavorFactory(cpu=24, ram=8192, disk=20)
        mfactory.VirtualMachineFactory(userid="user1", deleted=True)
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user1",
                                       operstate="BUILD")
        mfactory.VolumeFactory(userid="user1", size=20, machine=None)
        user_holdings = {"user1": {"user1": {"cyclades.vm": 1,
                                             "cyclades.total_cpu": 24,
                                             "cyclades.cpu": 24,
                                             "cyclades.disk": 20 << 30,
                                             "cyclades.total_ram": 8192 << 20,
                                             "cyclades.ram": 8192 << 20}}}
        holdings = util.get_db_holdings(user="user1")
        self.assertEqual(holdings, user_holdings)
        holdings = util.get_db_holdings()
        self.assertEqual(holdings["user1"], user_holdings["user1"])
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user1")
        ##
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user2",
                                       operstate="STARTED")
        mfactory.VolumeFactory(userid="user2", size=30, machine=None)
        user_holdings = {"user2": {"user2": {"cyclades.vm": 1,
                                             "cyclades.total_cpu": 24,
                                             "cyclades.cpu": 24,
                                             "cyclades.disk": 30 << 30,
                                             "cyclades.total_ram": 8192 << 20,
                                             "cyclades.ram": 8192 << 20}}}
        holdings = util.get_db_holdings(user="user2")
        self.assertEqual(holdings, user_holdings)
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user3",
                                       operstate="STOPPED")
        user_holdings = {"user3": {"user3": {"cyclades.vm": 1,
                                             "cyclades.total_cpu": 24,
                                             "cyclades.total_ram": 8589934592}}
                         }
        holdings = util.get_db_holdings(user="user3")
        self.assertEqual(holdings, user_holdings)

    def test_network_holdings(self):
        mfactory.NetworkFactory(userid="user1")
        mfactory.NetworkFactory(userid="user2")
        user_holdings = {"user2": {"user2": {"cyclades.network.private": 1}}}
        holdings = util.get_db_holdings(user="user2")
        self.assertEqual(holdings, user_holdings)
        holdings = util.get_db_holdings()
        self.assertEqual(holdings["user2"], user_holdings["user2"])

    def test_floating_ip_holdings(self):
        mfactory.IPv4AddressFactory(userid="user1", floating_ip=True)
        mfactory.IPv4AddressFactory(userid="user1", floating_ip=True)
        mfactory.IPv4AddressFactory(userid="user2", floating_ip=True)
        mfactory.IPv4AddressFactory(userid="user3", floating_ip=True)
        holdings = util.get_db_holdings()
        self.assertEqual(holdings["user1"]["user1"]["cyclades.floating_ip"], 2)
        self.assertEqual(holdings["user2"]["user2"]["cyclades.floating_ip"], 1)
        self.assertEqual(holdings["user3"]["user3"]["cyclades.floating_ip"], 1)


@patch("synnefo.quotas.get_quotaholder_pending")
class ResolvePendingTestCase(TestCase):
    def setUp(self):
        self.p1 = mfactory.QuotaHolderSerialFactory(serial=20, pending=True)
        self.p1 = mfactory.QuotaHolderSerialFactory(serial=30, pending=True)
        self.a1 = mfactory.QuotaHolderSerialFactory(serial=15, pending=False,
                                                    accept=True)
        self.a2 = mfactory.QuotaHolderSerialFactory(serial=25, pending=False,
                                                    accept=True)
        self.r1 = mfactory.QuotaHolderSerialFactory(serial=18, pending=False,
                                                    accept=False)
        self.r2 = mfactory.QuotaHolderSerialFactory(serial=23, pending=False,
                                                    accept=False)

    def test_no_pending(self, qh):
        qh.return_value = []
        pending = quotas.resolve_pending_commissions()
        self.assertEqual(pending, ([], []))

    def test_1(self, qh):
        qh.return_value = [21, 25, 28]
        pending = quotas.resolve_pending_commissions()
        self.assertEqual(pending, ([25], [28, 21]))


class GetCommissionInfoTest(TestCase):
    maxDiff = None

    def test_commissions(self):
        flavor = mfactory.FlavorFactory(cpu=2, ram=1024, disk=20)
        vm = mfactory.VirtualMachineFactory(flavor=flavor)
        mfactory.VolumeFactory(size=20, machine=vm, deleted=False,
                               status="IN_USE",
                               delete_on_termination=True)
        vm.volumes.update(project=vm.project)
        #commission = quotas.get_commission_info(vm, "BUILD")
        #self.assertEqual({"cyclades.vm": 1,
        #                  "cyclades.cpu": 2,
        #                  "cyclades.cpu": 2,
        #                  "cyclades.ram": 1048576 * 1024,
        #                  "cyclades.ram": 1048576 * 1024,
        #                  "cyclades.disk": 1073741824 * 20}, commission)
        vm.operstate = "STARTED"
        vm.save()
        project = vm.project
        commission = quotas.get_commission_info(vm, "STOP")
        self.assertEqual({(project, "cyclades.cpu"): -2,
                          (project, "cyclades.ram"): 1048576 * -1024}, commission)
        # Check None quotas if vm is already stopped
        vm.operstate = "STOPPED"
        vm.save()
        commission = quotas.get_commission_info(vm, "STOP")
        self.assertEqual(None, commission)
        commission = quotas.get_commission_info(vm, "START")
        self.assertEqual({(project, "cyclades.cpu"): 2,
                          (project, "cyclades.ram"): 1048576 * 1024}, commission)
        vm.operstate = "STARTED"
        vm.save()
        commission = quotas.get_commission_info(vm, "DESTROY")
        self.assertEqual({(project, "cyclades.vm"): -1,
                          (project, "cyclades.total_cpu"): -2,
                          (project, "cyclades.cpu"): -2,
                          (project, "cyclades.total_ram"): 1048576 * -1024,
                          (project, "cyclades.ram"): 1048576 * -1024,
                          (project, "cyclades.disk"): 1073741824 * -20}, commission)
        vm.operstate = "STOPPED"
        vm.save()
        commission = quotas.get_commission_info(vm, "DESTROY")
        self.assertEqual({(project, "cyclades.vm"): -1,
                          (project, "cyclades.total_cpu"): -2,
                          (project, "cyclades.total_ram"): -1024 << 20,
                          (project, "cyclades.disk"): -20 << 30}, commission)
        commission = quotas.get_commission_info(vm, "RESIZE")
        self.assertTrue((commission is None) or (not commission.keys()))

        commission = quotas.get_commission_info(vm, "RESIZE",
                                                {"beparams": {"vcpus": 4,
                                                              "maxmem": 2048}})
        self.assertEqual({(project, "cyclades.total_cpu"): 2,
                          (project, "cyclades.total_ram"): 1048576 * 1024}, commission)
        vm.operstate = "STOPPED"
        vm.save()
        commission = quotas.get_commission_info(vm, "REBOOT")
        self.assertEqual({(project, "cyclades.cpu"): 2,
                          (project, "cyclades.ram"): 1048576 * 1024}, commission)
        vm.operstate = "STARTED"
        vm.save()
        commission = quotas.get_commission_info(vm, "REBOOT")
        self.assertEqual(None, commission)

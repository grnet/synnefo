#!/usr/bin/env python
#
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
#
from mock import patch
from django.test import TestCase
from synnefo.db import models_factory as mfactory

from synnefo import quotas
from synnefo.quotas import util


class GetDBHoldingsTestCase(TestCase):
    def test_no_holdings(self):
        holdings = util.get_db_holdings(user=None)
        self.assertEqual(holdings, {})

    def test_vm_holdings(self):
        flavor = mfactory.FlavorFactory(cpu=24, ram=8192, disk=20,
                                        disk_template='drbd')
        mfactory.VirtualMachineFactory()
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user1",
                                       operstate="BUILD")
        user_holdings = {"user1": {"cyclades.vm": 1,
                                   "cyclades.cpu": 24,
                                   "cyclades.active_cpu": 24,
                                   "cyclades.disk": 21474836480,
                                   "cyclades.ram": 8589934592,
                                   "cyclades.active_ram": 8589934592}}
        holdings = util.get_db_holdings(user="user1")
        self.assertEqual(holdings, user_holdings)
        holdings = util.get_db_holdings()
        self.assertEqual(holdings["user1"], user_holdings["user1"])
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user1")
        ##
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user2",
                                       operstate="STARTED")
        user_holdings = {"user2": {"cyclades.vm": 1,
                                   "cyclades.cpu": 24,
                                   "cyclades.active_cpu": 24,
                                   "cyclades.disk": 21474836480,
                                   "cyclades.ram": 8589934592,
                                   "cyclades.active_ram": 8589934592}}
        holdings = util.get_db_holdings(user="user2")
        self.assertEqual(holdings, user_holdings)
        mfactory.VirtualMachineFactory(flavor=flavor, userid="user3",
                                       operstate="STOPPED")
        user_holdings = {"user3": {"cyclades.vm": 1,
                                   "cyclades.cpu": 24,
                                   "cyclades.disk": 21474836480,
                                   "cyclades.ram": 8589934592}}
        holdings = util.get_db_holdings(user="user3")
        self.assertEqual(holdings, user_holdings)


    def test_network_holdings(self):
        mfactory.NetworkFactory(userid="user1")
        mfactory.NetworkFactory(userid="user2")
        user_holdings = {"user2": {"cyclades.network.private": 1}}
        holdings = util.get_db_holdings(user="user2")
        self.assertEqual(holdings, user_holdings)
        holdings = util.get_db_holdings()
        self.assertEqual(holdings["user2"], user_holdings["user2"])

    def test_floating_ip_holdings(self):
        mfactory.IPAddressFactory(userid="user1")
        mfactory.IPAddressFactory(userid="user1")
        mfactory.IPAddressFactory(userid="user2")
        mfactory.IPAddressFactory(userid="user3")
        holdings = util.get_db_holdings()
        self.assertEqual(holdings["user1"]["cyclades.floating_ip"], 2)
        self.assertEqual(holdings["user2"]["cyclades.floating_ip"], 1)
        self.assertEqual(holdings["user3"]["cyclades.floating_ip"], 1)


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
    def test_commissions(self):
        flavor = mfactory.FlavorFactory(cpu=2, ram=1024, disk=20)
        vm = mfactory.VirtualMachineFactory(flavor=flavor)
        #commission = quotas.get_commission_info(vm, "BUILD")
        #self.assertEqual({"cyclades.vm": 1,
        #                  "cyclades.cpu": 2,
        #                  "cyclades.active_cpu": 2,
        #                  "cyclades.ram": 1048576 * 1024,
        #                  "cyclades.active_ram": 1048576 * 1024,
        #                  "cyclades.disk": 1073741824 * 20}, commission)
        vm.operstate = "STARTED"
        vm.save()
        commission = quotas.get_commission_info(vm, "STOP")
        self.assertEqual({"cyclades.active_cpu": -2,
                          "cyclades.active_ram": 1048576 * -1024}, commission)
        # Check None quotas if vm is already stopped
        vm.operstate = "STOPPED"
        vm.save()
        commission = quotas.get_commission_info(vm, "STOP")
        self.assertEqual(None, commission)
        commission = quotas.get_commission_info(vm, "START")
        self.assertEqual({"cyclades.active_cpu": 2,
                          "cyclades.active_ram": 1048576 * 1024}, commission)
        vm.operstate = "STARTED"
        vm.save()
        commission = quotas.get_commission_info(vm, "DESTROY")
        self.assertEqual({"cyclades.vm": -1,
                          "cyclades.cpu": -2,
                          "cyclades.active_cpu": -2,
                          "cyclades.ram": 1048576 * -1024,
                          "cyclades.active_ram": 1048576 * -1024,
                          "cyclades.disk": 1073741824 * -20}, commission)
        vm.operstate = "STOPPED"
        vm.save()
        commission = quotas.get_commission_info(vm, "DESTROY")
        self.assertEqual({"cyclades.vm": -1,
                          "cyclades.cpu": -2,
                          "cyclades.ram": 1048576 * -1024,
                          "cyclades.disk": 1073741824 * -20}, commission)
        commission = quotas.get_commission_info(vm, "RESIZE")
        self.assertEqual(None, commission)
        commission = quotas.get_commission_info(vm, "RESIZE",
                                                {"beparams": {"vcpus": 4,
                                                              "maxmem":2048}})
        self.assertEqual({"cyclades.cpu": 2,
                          "cyclades.ram": 1048576 * 1024}, commission)
        vm.operstate = "STOPPED"
        vm.save()
        commission = quotas.get_commission_info(vm, "REBOOT")
        self.assertEqual({"cyclades.active_cpu": 2,
                          "cyclades.active_ram": 1048576 * 1024}, commission)
        vm.operstate = "STARTED"
        vm.save()
        commission = quotas.get_commission_info(vm, "REBOOT")
        self.assertEqual(None, commission)

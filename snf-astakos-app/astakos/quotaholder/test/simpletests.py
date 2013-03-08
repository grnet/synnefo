# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from config import QHTestCase
from config import run_test_case
from config import printf

from astakos.quotaholder.exception import (
                            QuotaholderError,
                            InvalidDataError,
                            NoCapacityError,
                            NoStockError,
                            NonExportedError,
                            CommissionValueException,
                            DuplicateError)

from astakos.quotaholder.api import QH_PRACTICALLY_INFINITE
from astakos.quotaholder.utils.rand import random_int, random_nat, random_name

DEFAULT_HOLDING = (0, 0, 0, 0)

class QHAPITest(QHTestCase):

    @classmethod
    def setUpClass(self):
        QHTestCase.setUpClass()
        self.client = self.rand_holder()

    @classmethod
    def rand_name(self, exclude=None):
        for i in range(1,100):
            r = random_name()
            if exclude is not None and r not in exclude:
                exclude.append(r)
                return r
        else:
            m = 'Could not make a unique random name'
            raise Exception(m)

    used_entities = ['system']

    @classmethod
    def rand_holder(self):
        return self.rand_name(self.used_entities)

    used_resources = []

    @classmethod
    def rand_resource(self):
        return self.rand_name(self.used_resources)

    def rand_limits(self):
        c = random_nat()
        return (c,)

    def rand_flags(self):
        return random_nat()

    def rand_counters(self):
        return tuple(random_nat() for i in range(4))

    def new_policy(self):
        p, limits = self.rand_policy_limits()
        self.qh.set_limits(set_limits=[(p,) + limits])
        return p, limits

    @transaction.commit_on_success
    def test_0080_get_set_quota(self):
        e = self.rand_holder()
        resource = self.rand_resource()
        limits = self.rand_limits()
        limits1 = self.rand_limits()
        f = self.rand_flags()
        self.qh.set_quota(set_quota=[(e, resource) + limits + (f,),
                                     (e, resource) + limits1 + (f,)])

        resource2 = self.rand_resource()
        r = self.qh.get_quota(get_quota=[(e, resource),
                                         (e, resource2)])
        self.assertEqual(r, [(e, resource) + limits1 +
                             DEFAULT_HOLDING + (f,)])

    def new_quota(self, holder, resource, limits=None):
        if limits is None:
            limits = self.rand_limits()
        f = self.rand_flags()
        self.qh.set_quota(
            set_quota=[(holder, resource) + limits + (f,)])
        return limits

    @transaction.commit_on_success
    def test_0081_add_quota(self):
        e0 = self.rand_holder()
        e1 = self.rand_holder()
        resource0 = self.rand_resource()
        resource1 = self.rand_resource()

        self.qh.set_quota(
            set_quota=[(e0, resource0) + (QH_PRACTICALLY_INFINITE, 0),
                       (e1, resource0) + (5, 0)])

        self.qh.add_quota(sub_quota=[(e0, resource0,
                                      QH_PRACTICALLY_INFINITE)],
                          add_quota=[(e0, resource0,
                                      3),
                                     # new holding
                                     (e0, resource1,
                                      QH_PRACTICALLY_INFINITE)])

        r = self.qh.get_quota(get_quota=[(e0, resource0),
                                         (e0, resource1)])
        self.assertEqual(r, [(e0, resource0, 3)
                             + DEFAULT_HOLDING + (0,),
                             (e0, resource1, QH_PRACTICALLY_INFINITE)
                             + DEFAULT_HOLDING + (0,)])

        with self.assertRaises(QuotaholderError) as cm:
            self.qh.add_quota(add_quota=[(e1, resource0,
                                          (-10)),
                                         (e0, resource1, 0)])

        err = cm.exception
        self.assertEqual(err.message, [(e1, resource0)])

        # r = self.qh.get_quota(get_quota=[(e1, resource0),
        #                                  (e0, resource1)])
        # self.assertEqual(r, [(e1, resource0, 5, 5)
        #                      + DEFAULT_HOLDING + (0,),
        #                      (e0, resource1, 0, QH_PRACTICALLY_INFINITE)
        #                      + DEFAULT_HOLDING + (0,)])

    @transaction.commit_on_success
    def test_0082_max_quota(self):
        e0 = self.rand_holder()
        e1 = self.rand_holder()
        resource0 = self.rand_resource()
        resource1 = self.rand_resource()

        self.qh.set_quota(
            set_quota=[(e0, resource0) +
                       (QH_PRACTICALLY_INFINITE,) + (0,)])

        self.qh.add_quota(add_quota=[(e0, resource0,
                                      QH_PRACTICALLY_INFINITE)])

        r = self.qh.get_quota(get_quota=[(e0, resource0)])
        self.assertEqual(r, [(e0, resource0, 2*QH_PRACTICALLY_INFINITE)
                             + DEFAULT_HOLDING + (0,)])

    @transaction.commit_on_success
    def initialize_holding(self, holder, resource, quantity):
        s = self.qh.issue_commission(clientkey=self.client, target=holder,
                                     name='initialize',
                                     provisions=[(None, resource, quantity)])
        self.qh.accept_commission(clientkey=self.client, serials=[s])

    @transaction.commit_on_success
    def issue_commission(self, target, provisions):
        return self.qh.issue_commission(clientkey=self.client, target=target,
                                        name='something',
                                        provisions=provisions)

    @transaction.commit_on_success
    def test_0090_commissions(self):
        e0 = self.rand_holder()
        e1 = self.rand_holder()
        resource = self.rand_resource()
        c0, = self.new_quota(e0, resource)
        c1, = self.new_quota(e1, resource)

        self.initialize_holding(e1, resource, c1)

        most = min(c0, c1)
        if most < 0:
            raise AssertionError("%s <= 0" % most)

        s1 = self.issue_commission(target=e0,
                                   provisions=[(e1, resource, most)])
        self.assertGreater(s1, 0)

        with self.assertRaises(CommissionValueException):
            self.issue_commission(target=e0,
                                  provisions=[(e1, resource, 1)])

        r = self.qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(list(r), [s1])
        r = self.qh.resolve_pending_commissions(clientkey=self.client,
                                                max_serial=s1, accept_set=[s1])
        r = self.qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(list(r), [])

    @transaction.commit_on_success
    def test_0091_commissions_exceptions(self):
        es1 = self.rand_holder()
        es2 = self.rand_holder()
        et1 = self.rand_holder()
        et2 = self.rand_holder()
        resource = self.rand_resource()
        self.new_quota(es1, resource, (10,))
        self.new_quota(es2, resource, (10,))
        self.new_quota(et1, resource, (15,))
        self.new_quota(et2, resource, (15,))

        self.initialize_holding(es1, resource, 10)
        self.initialize_holding(es2, resource, 10)

        with self.assertRaises(NoStockError) as cm:
            self.qh.issue_commission(clientkey=self.client, target=et1,
                                     name='something',
                                     provisions=[(es1, resource, 12)])
        e = cm.exception
        self.assertEqual(e.holder, es1)
        self.assertEqual(e.resource, resource)
        self.assertEqual(int(e.limit), 10)
        self.assertEqual(int(e.requested), 12)

        r = self.qh.issue_commission(clientkey=self.client, target=et1,
                                     name='something',
                                     provisions=[(es1, resource, 2)])
        self.assertGreater(r, 0)



        r = self.qh.issue_commission(clientkey=self.client, target=et2,
                                     name='something',
                                     provisions=[(es2, resource, 9)])
        self.assertGreater(r, 0)

        with self.assertRaises(NoCapacityError) as cm:
            self.qh.issue_commission(clientkey=self.client, target=et2,
                                     name='something',
                                     provisions=[(es2, resource, 1),
                                                 (es1, resource, 6)])
        e = cm.exception
        self.assertEqual(e.holder, et2)
        self.assertEqual(e.resource, resource)
        self.assertEqual(int(e.limit), 15)
        self.assertEqual(int(e.requested), 6)
        # 9 actual + 1 from the first provision
        self.assertEqual(int(e.current), 10)

    @transaction.commit_on_success
    def test_010_list_holdings(self):
        e0 = 'list_holdings_one'
        e1 = 'list_holdings_two'
        resource = 'list_holdings_resource'
        sys = 'system'

        self.qh.set_quota(set_quota=[(sys, resource, 10, 0),
                                     (e0, resource, 10, 0),
                                     (e1, resource, 10, 0)])

        self.initialize_holding(sys, resource, 10)

        s0 = self.qh.issue_commission(clientkey=self.client, target=e0,
                                      name='a commission',
                                      provisions=[('system', resource, 3)])

        s1 = self.qh.issue_commission(clientkey=self.client, target=e1,
                                      name='a commission',
                                      provisions=[('system', resource, 4)])

        holdings_list, rejected = self.qh.list_holdings(
            list_holdings=[e0, e1, e0+e1])

        self.assertEqual(rejected, [e0+e1])
        self.assertEqual(holdings_list, [[(e0, resource, 0, 3, 0, 0)],
                                         [(e1, resource, 0, 4, 0, 0)]])

        self.qh.accept_commission(clientkey=self.client, serials=[s0, s1])

        holdings_list, rejected = self.qh.list_holdings(
            list_holdings=[e0, e1, e0+e1])

        self.assertEqual(rejected, [e0+e1])
        self.assertEqual(holdings_list, [[(e0, resource, 3, 3, 3, 3)],
                                         [(e1, resource, 4, 4, 4, 4)]])


    @transaction.commit_on_success
    def test_0130_release_holding(self):
        e = self.rand_holder()
        resource = self.rand_resource()
        limits = self.new_quota(e, resource, (2,))

        self.initialize_holding(e, resource, 1)

        with self.assertRaises(QuotaholderError) as cm:
            self.qh.release_holding(release_holding=[(e, resource)])

        err = cm.exception
        self.assertEqual(err.message, [0])

    @transaction.commit_on_success
    def test_0131_release_holding(self):
        e = self.rand_holder()
        resource = self.rand_resource()
        limits = self.new_quota(e, resource, (2,))

        self.qh.release_holding(release_holding=[(e, resource)])

    @transaction.commit_on_success
    def test_0132_release_holding(self):
        resource = self.rand_resource()

        es = self.rand_holder()
        limits_s = self.new_quota(es, resource, (3,))

        self.initialize_holding(es, resource, 3)

        e = self.rand_holder()
        limits = self.new_quota(e, resource, (2,))

        r = self.qh.issue_commission(clientkey=self.client, target=e,
                                     name='something',
                                     provisions=[(es, resource, 1)])
        self.assertGreater(r, 0)

        with self.assertRaises(QuotaholderError) as cm:
            self.qh.release_holding(release_holding=[(e, resource)])

        err = cm.exception
        self.assertEqual(err.message, [0])

    @transaction.commit_on_success
    def test_014_reset_holding(self):
        e0 = self.rand_holder()
        e1 = self.rand_holder()
        resource = self.rand_resource()
        c, = self.rand_limits()
        f = self.rand_flags()
        r = self.qh.set_quota(set_quota=[(e1, resource, c, f)])

        counters = self.rand_counters()

        with self.assertRaises(QuotaholderError) as cm:
            self.qh.reset_holding(
                reset_holding=[(e0, resource) + counters,
                               (e1, resource) + counters])

        err = cm.exception
        self.assertEqual(err.message, [0])

        r = self.qh.get_quota(get_quota=[(e1, resource)])
        self.assertEqual(r, [(e1, resource, c) + counters + (f,)])

    @transaction.commit_on_success
    def test_015_release_nocapacity(self):
        qh = self.qh
        owner = "system"
        source = "test_015_release_nocapacity_source"
        resource = "resource"
        target = "test_015_release_nocapacity_target"
        flags = 0

        qh.set_quota(set_quota=[(source, resource, 6, 0)])
        self.initialize_holding(source, resource, 6)

        qh.set_quota(set_quota=[(target, resource, 5, 0)])

        serial = qh.issue_commission(clientkey=self.client, target=target,
                                     name="something",
                                     provisions=[(source, resource, 5)])
        qh.accept_commission(clientkey=self.client, serials=[serial])

        holding = qh.get_quota(get_quota=[[source, resource]])
        self.assertEqual(tuple(holding[0]),
                         (source, resource, 6, 6, 6, 1, 1, flags))
        holding = qh.get_quota(get_quota=[[target, resource]])
        self.assertEqual(tuple(holding[0]),
                         (target, resource, 5, 5, 5, 5, 5, flags))

        if qh.reset_holding(
            reset_holding=[[target, resource, 10, 10, 10, 10]]):
            raise failed

        with self.assertRaises(NoCapacityError):
            qh.issue_commission(clientkey=self.client, target=target,
                                name="something",
                                provisions=[(source, resource, 1)])

        with self.assertRaises(NonExportedError):
            qh.issue_commission(clientkey=self.client, target=target,
                                name="something",
                                provisions=[(source, resource, -7)])

        serial = qh.issue_commission(clientkey=self.client, target=target,
                                     name="something",
                                     provisions=[(source, resource, -1)])
        qh.accept_commission(clientkey=self.client, serials=[serial])

        holding = qh.get_quota(get_quota=[[source, resource]])
        self.assertEqual(tuple(holding[0]),
                         (source, resource, 6, 6, 6, 2, 2, flags))
        holding = qh.get_quota(get_quota=[[target, resource]])
        self.assertEqual(tuple(holding[0]),
                         (target, resource, 5, 9, 9, 9, 9, flags))

        with self.assertRaises(NonExportedError):
            qh.issue_commission(clientkey=self.client, target=target,
                                name="something",
                                provisions=[(source, resource, -10)])


if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(QHAPITest)

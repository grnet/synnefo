# Copyright 2012 GRNET S.A. All rights reserved.
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
from config import rand_string
from config import printf

from synnefo.lib.commissioning import CallError
from synnefo.lib.quotaholder.api import (
                            InvalidDataError,
                            InvalidKeyError, NoEntityError,
                            NoQuantityError, NoCapacityError,
                            ExportLimitError, ImportLimitError,
                            DuplicateError)
from synnefo.lib.quotaholder.api.quotaholder import (
    Name, Key, Quantity, Capacity, ImportLimit, ExportLimit, Resource, Flags,
    Imported, Exported, Returned, Released)

QH_MAX_INT = 10**32

DEFAULT_HOLDING = (0, 0, 0, 0)

class QHAPITest(QHTestCase):

    @classmethod
    def setUpClass(self):
        QHTestCase.setUpClass()
        e = self.rand_entity()
        k = Key.random()
        r = self.qh.create_entity(create_entity=[(e, 'system', k, '')])
        self.e_name = e
        self.e_key = k
        self.client = self.rand_entity()

    @classmethod
    def rand_name(self, exclude=[]):
        for i in range(1,100):
            r = Name().random()
            if r not in exclude:
                exclude.append(r)
                return r
        else:
            m = 'Could not make a unique random name'
            raise Exception(m)

    used_entities = ['system']

    @classmethod
    def rand_entity(self):
        return self.rand_name(self.used_entities)

    used_policies = []

    @classmethod
    def rand_policy(self):
        return self.rand_name(self.used_policies)

    used_resources = []

    @classmethod
    def rand_resource(self):
        return self.rand_name(self.used_resources)

    def rand_limits(self):
        q = Capacity.random() # Nonnegative
        c = Capacity.random()
        il = ImportLimit.random()
        el = ExportLimit.random()
        return q, c, il, el

    def rand_policy_limits(self):
        p = self.rand_policy()
        limits = self.rand_limits()
        return p, limits

    def rand_flags(self):
        return Flags.random()

    def rand_counters(self):
        return (Imported.random(), Exported.random(),
                Returned.random(), Released.random())

    def new_entity(self, parent='system', parent_key=''):
        e = self.rand_entity()
        k = Key.random()
        r = self.qh.create_entity(create_entity=[(e, parent, k, parent_key)])
        self.assertEqual(r, [])
        return e, k

    def new_policy(self):
        p, limits = self.rand_policy_limits()
        r = self.qh.set_limits(set_limits=[(p,) + limits])
        self.assertEqual(r, [])
        return p, limits

    def test_001_list_entities(self):
        r = self.qh.list_entities(entity='system', key='')
        self.assertEqual(sorted(r), sorted(['system', self.e_name]))

        with self.assertRaises(NoEntityError):
            self.qh.list_entities(entity='doesnotexist', key='')

        with self.assertRaises(InvalidDataError):
            self.qh.list_entities(entity='system; SELECT ALL', key='')

    def test_002_create_entity(self):
        e = self.rand_entity()
        k = Key.random()
        r = self.qh.create_entity(
            create_entity=[(self.e_name, 'system', self.e_key, ''),
                           (e, self.e_name, k, self.e_key),
                           (e, self.e_name, k, self.e_key)])
        self.assertEqual(r, [0,2])

    def test_003_release_entity(self):
        e, k = self.new_entity()
        r = self.qh.release_entity(release_entity=[(e, k)])
        self.assertEqual(r, [])

    def test_004_set_entity_key(self):
        e, k = self.new_entity()
        k1 = Key.random()
        k2 = Key.random()
        r = self.qh.set_entity_key(set_entity_key=[(e, k1, k2)])
        self.assertEqual(r, [e])
        r = self.qh.set_entity_key(set_entity_key=[(e, k, k2)])
        self.assertEqual(r, [])
        r = self.qh.release_entity(release_entity=[(e, k)])
        self.assertEqual(r, [e])

    def test_005_get_entity(self):
        e = self.rand_entity()
        k = Key.random()
        r = self.qh.get_entity(get_entity=[(self.e_name, self.e_key), (e, k)])
        self.assertEqual(r, [(self.e_name, 'system')])

    def test_006_get_set_limits(self):

        p1, limits1 = self.rand_policy_limits()
        limits2 = self.rand_limits()
        r = self.qh.set_limits(set_limits=[(p1,) + limits1,
                                           (p1,) + limits2])
        self.assertEqual(r, [])

        p2, _ = self.rand_policy_limits()
        r = self.qh.get_limits(get_limits=[p1, p2])
        self.assertEqual(r, [(p1,) + limits2])

    def test_007_get_set_holding(self):
        e, k = self.new_entity()
        resource = self.rand_resource()

        p0 = self.rand_policy()
        f0 = self.rand_flags()
        p1, _ = self.new_policy()
        f1 = self.rand_flags()
        p2, _ = self.new_policy()
        f2 = self.rand_flags()

        # none is committed
        r = self.qh.set_holding(set_holding=[(e, resource, k, p0, f0),
                                             (e, resource, k, p1, f1),
                                             (e, resource, k, p2, f2)])
        self.assertEqual(r, [(e, resource, p0)])

        r = self.qh.get_holding(get_holding=[(e, resource, k)])
        self.assertEqual(r, [])

        r = self.qh.set_holding(set_holding=[(e, resource, k, p1, f1),
                                             (e, resource, k, p2, f2)])
        self.assertEqual(r, [])

        resource1 = self.rand_resource()
        r = self.qh.get_holding(get_holding=[(e, resource, k),
                                             (e, resource1, k)])
        self.assertEqual(r, [(e, resource, p2) + DEFAULT_HOLDING + (f2,)])

    def test_008_get_set_quota(self):
        e, k = self.new_entity()
        resource = self.rand_resource()
        limits = self.rand_limits()
        limits1 = self.rand_limits()
        f = self.rand_flags()
        r = self.qh.set_quota(set_quota=[(e, resource, k) + limits + (f,),
                                         (e, resource, k) + limits1 + (f,)])
        self.assertEqual(r, [])

        resource2 = self.rand_resource()
        r = self.qh.get_quota(get_quota=[(e, resource, k),
                                         (e, resource2, k)])
        self.assertEqual(r, [(e, resource) + limits1 +
                             DEFAULT_HOLDING + (f,)])

    def new_quota(self, entity, key, resource, limits=None):
        if limits is None:
            limits = self.rand_limits()
        f = self.rand_flags()
        r = self.qh.set_quota(
            set_quota=[(entity, resource, key) + limits + (f,)])
        self.assertEqual(r, [])
        return limits

    def test_0081_add_quota(self):
        e0, k0 = self.new_entity()
        e1, k1 = self.new_entity()
        resource0 = self.rand_resource()
        resource1 = self.rand_resource()

        r = self.qh.set_quota(
            set_quota=[(e0, resource0, k0) + (5, QH_MAX_INT, 5, 6) + (0,),
                       (e1, resource0, k1) + (5, 5, 5, 5) + (0,)])
        self.assertEqual(r, [])

        r = self.qh.add_quota(clientkey=self.client,
                              serial=1,
                              sub_quota=[(e0, resource0, k0, 0, QH_MAX_INT, 1, 1)],
                              add_quota=[(e0, resource0, k0, 0, 3, QH_MAX_INT, 0),
                                         # new holding
                                         (e0, resource1, k0, 0, QH_MAX_INT, 5, 5)])
        self.assertEqual(r, [])

        r = self.qh.get_quota(get_quota=[(e0, resource0, k0),
                                         (e0, resource1, k0)])
        self.assertEqual(r, [(e0, resource0, 5, 3, QH_MAX_INT, 5)
                             + DEFAULT_HOLDING + (0,),
                             (e0, resource1, 0, QH_MAX_INT, 5, 5)
                             + DEFAULT_HOLDING + (0,)])

        # repeated serial
        r = self.qh.add_quota(clientkey=self.client,
                              serial=1,
                              sub_quota=[(e0, resource1, k0, 0, QH_MAX_INT, (-5), 0)],
                              add_quota=[(e0, resource0, k0, 0, 2, QH_MAX_INT, 0)])
        self.assertEqual(r, [(e0, resource1), (e0, resource0)])

        r = self.qh.query_serials(clientkey=self.client, serials=[1, 2])
        self.assertEqual(r, [1])

        r = self.qh.query_serials(clientkey=self.client, serials=[])
        self.assertEqual(r, [1])

        r = self.qh.query_serials(clientkey=self.client, serials=[2])
        self.assertEqual(r, [])

        r = self.qh.ack_serials(clientkey=self.client, serials=[1])

        r = self.qh.query_serials(clientkey=self.client, serials=[1, 2])
        self.assertEqual(r, [])

        # idempotent
        r = self.qh.ack_serials(clientkey=self.client, serials=[1])

        # serial has been deleted
        r = self.qh.add_quota(clientkey=self.client,
                              serial=1,
                              add_quota=[(e0, resource0, k0, 0, 2, QH_MAX_INT, 0)])
        self.assertEqual(r, [])

        # none is committed
        r = self.qh.add_quota(clientkey=self.client,
                              serial=2,
                              add_quota=[(e1, resource0, k1, 0, (-10), QH_MAX_INT, 0),
                                         (e0, resource1, k0, 1, 0, 0, 0)])
        self.assertEqual(r, [(e1, resource0)])

        r = self.qh.get_quota(get_quota=[(e1, resource0, k1),
                                         (e0, resource1, k0)])
        self.assertEqual(r, [(e1, resource0, 5, 5 , 5, 5)
                             + DEFAULT_HOLDING + (0,),
                             (e0, resource1, 0, QH_MAX_INT, 5, 5)
                             + DEFAULT_HOLDING + (0,)])

    def test_0082_max_quota(self):
        e0, k0 = self.new_entity()
        e1, k1 = self.new_entity()
        resource0 = self.rand_resource()
        resource1 = self.rand_resource()

        r = self.qh.set_quota(
            set_quota=[(e0, resource0, k0) + (5, QH_MAX_INT, 5, 6) + (0,)])
        self.assertEqual(r, [])

        r = self.qh.add_quota(clientkey=self.client,
                              serial=3,
                              add_quota=[(e0, resource0, k0, 0, QH_MAX_INT, 0, 0)])

        self.assertEqual(r, [])

        r = self.qh.get_quota(get_quota=[(e0, resource0, k0)])
        self.assertEqual(r, [(e0, resource0, 5, 2*QH_MAX_INT, 5, 6)
                             + DEFAULT_HOLDING + (0,)])



    def test_0090_commissions(self):
        e0, k0 = self.new_entity()
        e1, k1 = self.new_entity()
        resource = self.rand_resource()
        q0, c0, il0, el0 = self.new_quota(e0, k0, resource)
        q1, c1, il1, el1 = self.new_quota(e1, k1, resource)

        most = max(0, min(c0, il0, q1, el1))
        r = self.qh.issue_commission(clientkey=self.client, target=e0, key=k0,
                                     name='something',
                                     provisions=[(e1, resource, most)])
        self.assertEqual(r, 1)

        with self.assertRaises(CallError):
            self.qh.issue_commission(clientkey=self.client, target=e0, key=k0,
                                     name='something',
                                     provisions=[(e1, resource, 1)])

        r = self.qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(r, [1])
        r = self.qh.resolve_pending_commissions(clientkey=self.client,
                                                max_serial=1, accept_set=[1])
        r = self.qh.get_pending_commissions(clientkey=self.client)
        self.assertEqual(r, [])

    def test_0091_commissions_exceptions(self):
        es1, ks1 = self.new_entity()
        es2, ks2 = self.new_entity()
        et1, kt1 = self.new_entity()
        et2, kt2 = self.new_entity()
        resource = self.rand_resource()
        self.new_quota(es1, ks1, resource, (10, 5, 5, 15))
        self.new_quota(es2, ks2, resource, (10, 5, 5, 10))
        self.new_quota(et1, kt1, resource, (0, 15, 3, 20))
        self.new_quota(et2, kt2, resource, (0, 15, 20, 20))

        try:
            self.qh.issue_commission(clientkey=self.client, target=et1, key=kt1,
                                     name='something',
                                     provisions=[(es1, resource, 12)])
        except NoQuantityError, e:
            self.assertEqual(e.source, es1)
            self.assertEqual(e.target, et1)
            self.assertEqual(e.resource, resource)
            self.assertEqual(e.limit, 10)
            self.assertEqual(e.requested, 12)
            self.assertEqual(e.current, 0)

            r = self.qh.issue_commission(clientkey=self.client, target=et1,
                                         key=kt1,
                                         name='something',
                                         provisions=[(es1, resource, 2)])
            self.assertGreater(r, 0)

        try:
            self.qh.issue_commission(clientkey=self.client, target=et1, key=kt1,
                                     name='something',
                                     provisions=[(es1, resource, 2)])
        except ImportLimitError, e:
            self.assertEqual(e.source, es1)
            self.assertEqual(e.target, et1)
            self.assertEqual(e.resource, resource)
            self.assertEqual(e.limit, 3)
            self.assertEqual(e.requested, 2)
            self.assertEqual(e.current, 2)

            r = self.qh.issue_commission(clientkey=self.client, target=et2,
                                         key=kt2,
                                         name='something',
                                         provisions=[(es2, resource, 9)])
            self.assertGreater(r, 0)

        try:
            self.qh.issue_commission(clientkey=self.client, target=et2,
                                     key=kt2,
                                     name='something',
                                     provisions=[(es2, resource, 1),
                                                 (es1, resource, 2)])
        except NoCapacityError, e:
            self.assertEqual(e.source, es1)
            self.assertEqual(e.target, et2)
            self.assertEqual(e.resource, resource)
            self.assertEqual(e.limit, 10)
            self.assertEqual(e.requested, 2)
            # 9 actual + 1 from the first provision
            self.assertEqual(e.current, 10)


    def test_010_list_holdings(self):
        e0, k0 = ('list_holdings_one', '1')
        e1, k1 = ('list_holdings_two', '1')
        resource = 'list_holdings_resource'
        sys = 'system'

        r = self.qh.create_entity(create_entity=[(e0, sys, k0, ''),
                                                 (e1, sys, k1, '')])
        if r:
            raise AssertionError("cannot create entities")

        self.qh.set_quota(set_quota=[(sys, resource, '', 10, 0, None, None, 0),
                                     (e0, resource, k0, 0, 10, None, None, 0),
                                     (e1, resource, k1, 0, 10, None, None, 0)])

        s0 = self.qh.issue_commission(clientkey=self.client, target=e0, key=k0,
                                      name='a commission',
                                      provisions=[('system', resource, 3)])

        s1 = self.qh.issue_commission(clientkey=self.client, target=e1, key=k1,
                                      name='a commission',
                                      provisions=[('system', resource, 4)])

        self.qh.accept_commission(clientkey=self.client, serials=[s0, s1])

        holdings_list, rejected = self.qh.list_holdings(list_holdings=[
                                                        (e0, k0),
                                                        (e1, k1),
                                                        (e0+e1, k0+k1)])

        self.assertEqual(rejected, [e0+e1])
        self.assertEqual(holdings_list, [[(e0, resource, 3, 0, 0, 0)],
                                         [(e1, resource, 4, 0, 0, 0)]])


    def test_011_release_empty(self):
        e, k = self.new_entity()
        e0, k0 = self.rand_entity(), Key.random()

        # none is committed
        r = self.qh.release_entity(release_entity=[(e, k), (e0, k0)])
        self.assertEqual(r, [e0])

        r = self.qh.get_entity(get_entity=[(e, k)])
        self.assertEqual(r, [(e, 'system')])

        r = self.qh.release_entity(release_entity=[(e, k)])
        self.assertEqual(r, [])

        r = self.qh.get_entity(get_entity=[(e, k)])
        self.assertEqual(r, [])

    def test_012_release_nonempty(self):
        e, k = self.new_entity()
        e1, k1 = self.new_entity(e, k)

        # none is committed
        r = self.qh.release_entity(release_entity=[(e, k), (e1, k1)])
        self.assertEqual(r, [e])

        r = self.qh.get_entity(get_entity=[(e1, k1)])
        self.assertEqual(r, [(e1, e)])

        r = self.qh.release_entity(release_entity=[(e1, k1), (e, k)])
        self.assertEqual(r, [])

        r = self.qh.get_entity(get_entity=[(e1, k1)])
        self.assertEqual(r, [])

    def test_013_release_nonempty(self):
        e, k = self.new_entity()
        resource = self.rand_resource()
        limits = self.new_quota(e, k, resource)
        r = self.qh.release_entity(release_entity=[(e, k)])
        self.assertEqual(r, [e])
        r = self.qh.release_holding(release_holding=[(e, resource, k)])
        self.assertEqual(r, [])
        r = self.qh.release_entity(release_entity=[(e, k)])
        self.assertEqual(r, [])

    def test_014_reset_holding(self):
        e0, k0 = self.new_entity()
        e1, k1 = self.new_entity()
        resource = self.rand_resource()
        p, _ = self.new_policy()
        f = self.rand_flags()
        r = self.qh.set_holding(set_holding=[(e1, resource, k1, p, f)])

        counters = self.rand_counters()

        # none is committed
        r = self.qh.reset_holding(
            reset_holding=[(e0, resource, k0) + counters,
                           (e1, resource, k1) + counters])
        self.assertEqual(r, [0])

        r = self.qh.get_holding(get_holding=[(e1, resource, k1)])
        self.assertEqual(r, [(e1, resource, p) + DEFAULT_HOLDING + (f,)])

        r = self.qh.reset_holding(
            reset_holding=[(e1, resource, k1) + counters])
        self.assertEqual(r, [])

        r = self.qh.get_holding(get_holding=[(e1, resource, k1)])
        self.assertEqual(r, [(e1, resource, p) + counters + (f,)])


if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(QHAPITest)

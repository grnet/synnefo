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

from synnefo.lib.quotaholder.api import InvalidDataError, NoEntityError
from synnefo.lib.quotaholder.api.quotaholder import (
    Name, Key, Quantity, Capacity, ImportLimit, ExportLimit, Resource, Flags)

DEFAULT_IMPORTED = 0
DEFAULT_EXPORTED = 0
DEFAULT_RETURNED = 0
DEFAULT_RELEASED = 0

class QHAPITest(QHTestCase):

    @classmethod
    def setUpClass(self):
        QHTestCase.setUpClass()
        e = self.rand_entity()
        k = Key.random()
        r = self.qh.create_entity(create_entity=[(e, 'system', k, '')])
        self.e_name = e
        self.e_key = k

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
        q = Quantity.random()
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
        self.assertEqual(r, ['system', self.e_name])

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
        r = self.qh.set_holding(set_holding=[(e, resource, k, p0, f0),
                                             (e, resource, k, p1, f1),
                                             (e, resource, k, p2, f2)])
        self.assertEqual(r, [(e, resource, p0)])

        resource1 = self.rand_resource()
        r = self.qh.get_holding(get_holding=[(e, resource, k),
                                             (e, resource1, k)])
        self.assertEqual(r, [(e, resource, p2,
                              DEFAULT_IMPORTED, DEFAULT_EXPORTED,
                              DEFAULT_RETURNED, DEFAULT_RELEASED,
                              f2)])

if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(QHAPITest)

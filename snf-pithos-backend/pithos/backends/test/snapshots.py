# Copyright (C) 2014 GRNET S.A.
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

import uuid as uuidlib

from pithos.backends.base import (IllegalOperationError, NotAllowedError,
                                  ItemNotExists, BrokenSnapshot,
                                  MAP_ERROR, MAP_UNAVAILABLE, MAP_AVAILABLE)


class TestSnapshotsMixin(object):
    def test_copy_snapshot(self):
        name = 'snf-snap-1-1'
        t = [self.account, self.account, 'snapshots', name]
        mapfile = 'archip:%s' % name
        self.b.register_object_map(*t, size=100,
                                   type='application/octet-stream',
                                   mapfile=mapfile)

        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], MAP_UNAVAILABLE)
        self.assertTrue('mapfile' in meta)
        self.assertEqual(meta['mapfile'], mapfile)
        self.assertTrue('is_snapshot' in meta)
        self.assertEqual(meta['is_snapshot'], True)

        dest_name = 'snf-snap-1-2'
        t2 = [self.account, self.account, 'snapshots', dest_name]
        self.assertRaises(NotAllowedError, self.b.copy_object, *(t + t2[1:]),
                          type='application/octet-stream', domain='snapshots')

        self.assertRaises(ItemNotExists, self.b.get_object_meta, *t2)

        meta2 = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta2)
        self.assertEqual(meta['available'], meta2['available'])
        self.assertTrue('mapfile' in meta2)
        self.assertTrue(meta['mapfile'] == meta2['mapfile'])
        self.assertTrue('is_snapshot' in meta2)
        self.assertEqual(meta['is_snapshot'], meta2['is_snapshot'])
        self.assertTrue('uuid' in meta2)
        uuid = meta2['uuid']

        self.assertRaises(AssertionError, self.b.update_object_status, uuid, 'invalid_state')
        self.assertRaises(NameError, self.b.update_object_status, str(uuidlib.uuid4()), -1)

        self.b.update_object_status(uuid, MAP_ERROR)

        meta3 = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta3)
        self.assertEqual(meta3['available'], MAP_ERROR)

        self.assertRaises(BrokenSnapshot, self.b.get_object_hashmap, *t)

        self.b.update_object_status(uuid, MAP_AVAILABLE)

        meta4 = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta4)
        self.assertEqual(meta4['available'], MAP_AVAILABLE)

    def test_move_snapshot(self):
        name = 'snf-snap-2-1'
        t = [self.account, self.account, 'snapshots', name]
        mapfile = 'archip:%s' % name
        self.b.register_object_map(*t, size=100,
                                   type='application/octet-stream',
                                   mapfile=mapfile)

        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], MAP_UNAVAILABLE)
        self.assertTrue('mapfile' in meta)
        self.assertEqual(meta['mapfile'], mapfile)
        self.assertTrue('is_snapshot' in meta)
        self.assertEqual(meta['is_snapshot'], True)

        dest_name = 'snf-snap-2-2'
        t2 = [self.account, self.account, 'snapshots', dest_name]
        self.b.move_object(*(t + t2[1:]), type='application/octet-stream',
                           domain='snapshots')

        meta2 = self.b.get_object_meta(*t2, include_user_defined=False)
        self.assertTrue('available' in meta2)
        self.assertEqual(meta['available'], meta2['available'])
        self.assertTrue('mapfile' in meta2)
        self.assertEqual(meta['mapfile'], meta2['mapfile'])
        self.assertTrue('is_snapshot', meta2['is_snapshot'])
        self.assertEqual(meta['is_snapshot'], meta2['is_snapshot'])

    def test_update_snapshot(self):
        name = 'snf-snap-3-1'
        mapfile = 'archip:%s' % name
        t = [self.account, self.account, 'snapshots', name]
        self.b.register_object_map(*t, size=100,
                                   type='application/octet-stream',
                                   mapfile=mapfile)
        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], MAP_UNAVAILABLE)
        self.assertTrue('mapfile' in meta)
        self.assertEqual(meta['mapfile'], mapfile)
        self.assertTrue('is_snapshot' in meta)
        self.assertEqual(meta['is_snapshot'], True)

        domain = 'plankton'
        self.b.update_object_meta(*t, domain=domain, meta={'foo': 'bar'})
        meta2 = self.b.get_object_meta(*t, domain=domain,
                                       include_user_defined=True)
        self.assertTrue('available' in meta2)
        self.assertEqual(meta2['available'], MAP_UNAVAILABLE)
        self.assertTrue('mapfile' in meta2)
        self.assertEqual(meta2['mapfile'], mapfile)
        self.assertTrue('is_snapshot' in meta2)
        self.assertEqual(meta2['is_snapshot'], True)
        self.assertTrue('foo' in meta2)
        self.assertTrue(meta2['foo'], 'bar')

        try:
            self.b.update_object_hashmap(*t, size=0,
                                         type='application/octet-stream',
                                         hashmap=(), checksum='',
                                         domain='plankton')
        except IllegalOperationError:
            meta = self.b.get_object_meta(*t, include_user_defined=False)
            self.assertTrue('available' in meta)
            self.assertEqual(meta['available'], MAP_UNAVAILABLE)
            self.assertTrue('mapfile' in meta)
            self.assertEqual(meta['mapfile'], mapfile)
            self.assertTrue('is_snapshot' in meta)
            self.assertEqual(meta['is_snapshot'], True)
        else:
            self.fail('Update snapshot should not be allowed')

    def test_get_domain_objects(self):
        name = 'snf-snap-1-1'
        t = [self.account, self.account, 'snapshots', name]
        mapfile = 'archip:%s' % name
        uuid = self.b.register_object_map(*t,
                                          domain='test',
                                          size=100,
                                          type='application/octet-stream',
                                          mapfile=mapfile,
                                          meta={'foo': 'bar'})
        try:
            objects = self.b.get_domain_objects(domain='test',
                                                user=self.account)
        except:
            self.fail('It shouldn\'t have arrived here.')
        else:
            self.assertEqual(len(objects), 1)
            path, meta, permissios = objects[0]
            self.assertEqual(path, '/'.join(t[1:]))
            self.assertTrue('uuid' in meta)
            self.assertEqual(meta['uuid'], uuid)
            self.assertTrue('available' in meta)
            self.assertEqual(meta['available'], MAP_UNAVAILABLE)

        objects = self.b.get_domain_objects(domain='test', user='somebody_else', check_permissions=True)
        self.assertEqual(objects, [])

        objects = self.b.get_domain_objects(domain='test', user=None, check_permissions=True)
        self.assertEqual(objects, [])

        objects = self.b.get_domain_objects(domain='test', user=None, check_permissions=False)
        self.assertEqual(len(objects), 1)
        path, meta, permissios = objects[0]
        self.assertEqual(path, '/'.join(t[1:]))
        self.assertTrue('uuid' in meta)
        self.assertEqual(meta['uuid'], uuid)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], MAP_UNAVAILABLE)

        objects = self.b.get_domain_objects(domain='test', user='somebody_else', check_permissions=False)
        self.assertEqual(len(objects), 1)
        path, meta, permissios = objects[0]
        self.assertEqual(path, '/'.join(t[1:]))
        self.assertTrue('uuid' in meta)
        self.assertEqual(meta['uuid'], uuid)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], MAP_UNAVAILABLE)

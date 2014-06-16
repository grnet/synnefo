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


class TestSnapshotsMixin(object):
    def test_copy_snapshot(self):
        name = 'snf-snap-1-1'
        t = [self.account, self.account, 'snapshots', name]
        self.b.register_object_map(*t, size=100,
                                   type='application/octet-stream',
                                   mapfile='archip:%s' % name)

        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], False)

        dest_name = 'snf-snap-1-2'
        t2 = [self.account, self.account, 'snapshots', dest_name]
        self.b.copy_object(*(t + t2[1:]), type='application/octet-stream',
                           domain='snapshots')

        meta2 = self.b.get_object_meta(*t2, include_user_defined=False)
        self.assertTrue('available' in meta2)
        self.assertEqual(meta['available'], meta2['available'])

    def test_move_snapshot(self):
        name = 'snf-snap-1-1'
        t = [self.account, self.account, 'snapshots', name]
        self.b.register_object_map(*t, size=100,
                                   type='application/octet-stream',
                                   mapfile='archip:%s' % name)

        meta = self.b.get_object_meta(*t, include_user_defined=False)
        self.assertTrue('available' in meta)
        self.assertEqual(meta['available'], False)

        dest_name = 'snf-snap-1-2'
        t2 = [self.account, self.account, 'snapshots', dest_name]
        self.b.move_object(*(t + t2[1:]), type='application/octet-stream',
                           domain='snapshots')

        meta2 = self.b.get_object_meta(*t2, include_user_defined=False)
        self.assertTrue('available' in meta2)
        self.assertEqual(meta['available'], meta2['available'])

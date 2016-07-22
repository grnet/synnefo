# Copyright (C) 2010-2016 GRNET S.A.
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

from django.test import TestCase

from synnefo.admin import stats

from mock import patch

class StatsTest(TestCase):
    def setUp(self):
        self.stats = stats

    def test_get_public_stats_from_cache(self):
        def get_mock(key):
            if key == 'active_servers':
                return 1
            if key == 'spawned_servers':
                return 2
            if key == 'spawned_networks':
                return 3

            return -1

        with patch('synnefo.api.util.public_stats_cache.get', get_mock):
            cached_stats = self.stats.get_public_stats_from_cache()

        self.assertEqual(cached_stats['active_servers'], 1)
        self.assertEqual(cached_stats['spawned_servers'], 2)
        self.assertEqual(cached_stats['spawned_networks'], 3)

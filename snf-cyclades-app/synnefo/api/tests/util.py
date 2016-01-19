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
from django.core.cache import cache

from synnefo.api.util import PublicStatsCache
from synnefo.db import models_factory


class PublicStatsCacheTest(TestCase):
    prefix = 'PublicStatsCache_user_'

    def setUp(self):
        self.memory_cache = PublicStatsCache()
        cache.clear()

    def create_virtual_machine(self, operstate=''):
        vm = models_factory.VirtualMachineFactory()
        if operstate:
            vm.operstate = operstate
            vm.save()

        return vm

    def create_network(self, state=''):
        network = models_factory.NetworkFactory()
        if state:
            network.state = state
            network.save()

        return network

    def get_stats_from_cache(self):
        spawned_servers = cache.get(self.prefix + 'spawned_servers')
        active_servers = cache.get(self.prefix + 'active_servers')
        spawned_networks = cache.get(self.prefix + 'spawned_networks')

        return {
            'spawned_servers': spawned_servers,
            'active_servers': active_servers,
            'spawned_networks': spawned_networks,
        }

    def test_inherits_MemoryCache(self):
        self.assertTrue(issubclass(PublicStatsCache, MemoryCache))

    def test_populate(self):
        """populate should query the database and store
        3 values in the cache:

        - spawned_servers
        - active_servers
        - spawned_networks

        """
        # 1 active-spawned server
        self.create_virtual_machine()
        # 1 spawned server
        self.create_virtual_machine(operstate="DELETED")
        # not spawned or active server
        self.create_virtual_machine(operstate="ERROR")

        # 1 spawned network
        self.create_network()
        # 1 not spawned network
        self.create_network(state="ERROR")

        expected_stats = {
            'spawned_servers': 2,
            'active_servers': 1,
            'spawned_networks': 1
        }

        self.memory_cache.populate()

        cached_stats = self.get_stats_from_cache()

        self.assertEqual(expected_stats, cached_stats)

        # create new active-spawned server
        self.create_virtual_machine()
        expected_stats['spawned_servers'] += 1
        expected_stats['active_servers'] += 1

        self.memory_cache.populate()
        cached_stats = self.get_stats_from_cache()

        self.assertEqual(expected_stats, cached_stats)

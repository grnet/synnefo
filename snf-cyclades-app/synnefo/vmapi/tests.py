# -*- coding: utf8 -*-
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

from django.test import TestCase
from django.utils import simplejson as json

from synnefo.lib import join_urls
from synnefo.vmapi import settings

from synnefo.cyclades_settings import cyclades_services, BASE_HOST
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls


class VMAPITest(TestCase):
    def setUp(self, *args, **kwargs):
        super(VMAPITest, self).setUp(*args, **kwargs)
        self.api_path = get_service_path(cyclades_services, 'vmapi',
                                         version='v1.0')
    def myget(self, path, *args, **kwargs):
        path = join_urls(self.api_path, path)
        return self.client.get(path, *args, **kwargs)

    def myput(self, path, *args, **kwargs):
        path = join_urls(self.api_path, path)
        return self.client.put(path, *args, **kwargs)

    def mypost(self, path, *args, **kwargs):
        path = join_urls(self.api_path, path)
        return self.client.post(path, *args, **kwargs)

    def mydelete(self, path, *args, **kwargs):
        path = join_urls(self.api_path, path)
        return self.client.delete(path, *args, **kwargs)


class TestServerParams(VMAPITest):

    def test_cache_backend(self):
        from synnefo.vmapi import backend
        backend.set("test", 1)
        self.assertEqual(backend.get("test"), 1)
        backend.set("test", None)
        self.assertEqual(backend.get("test"), None)

    def test_get_key(self):
        from synnefo.vmapi import get_key
        self.assertEqual(get_key("snf-1", "12345"), "vmapi_snf-1_12345")
        self.assertEqual(get_key("snf-1", None, "12345"), "vmapi_snf-1_12345")

    def test_params_create(self):
        from synnefo.vmapi.models import create_server_params
        from synnefo.vmapi import backend
        try:
            from synnefo.db.models import VirtualMachine
        except ImportError:
            print "Skipping test_params_create"
            return

        # mimic server creation signal called
        vm = VirtualMachine()
        params = {'password': 'X^942Jjfdsa', 'personality': {}}
        uuid = create_server_params(sender=vm, created_vm_params=params)

        self.assertEqual(vm.config_url,
                         join_urls(BASE_HOST, self.api_path,
                                   'server-params/%s' % uuid))
        key = "vmapi_%s" % uuid
        self.assertEqual(type(backend.get(key)), str)
        data = json.loads(backend.get(key))
        self.assertEqual('password' in data, True)
        self.assertEqual('personality' in data, True)
        self.assertEqual(data.get('password'), 'X^942Jjfdsa')

        response = self.myget('server-params/%s' % uuid)
        self.assertEqual(response.status_code, 200)
        response = self.myget('server-params/%s' % uuid)
        self.assertEqual(response.status_code, 404)

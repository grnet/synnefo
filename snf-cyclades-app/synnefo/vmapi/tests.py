# -*- coding: utf8 -*-
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

from django.test import TestCase
from django.utils import simplejson as json

from synnefo.vmapi import settings

class TestServerParams(TestCase):

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
            from synnefo.api.servers import server_created
            from synnefo.db.models import VirtualMachine
        except ImportError:
            print "Skipping test_params_create"
            return

        # mimic server creation signal called
        vm = VirtualMachine()
        params = {'password': 'X^942Jjfdsa', 'personality': {}}
        uuid = create_server_params(sender=vm, created_vm_params=params)

        self.assertEqual(vm.config_url, settings.BASE_URL + '/vmapi/server-params/%s' % uuid)
        key = "vmapi_%s" % uuid
        self.assertEqual(type(backend.get(key)), str)
        data = json.loads(backend.get(key))
        self.assertEqual('password' in data, True)
        self.assertEqual('personality' in data, True)
        self.assertEqual(data.get('password'), 'X^942Jjfdsa')

        response = self.client.get('/vmapi/server-params/%s' % uuid)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/vmapi/server-params/%s' % uuid)
        self.assertEqual(response.status_code, 404)


    def test_params_view(self):
        pass


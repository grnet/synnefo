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

from __future__ import with_statement

from django.utils import simplejson as json
from django.test import TestCase

from mock import patch
from contextlib import contextmanager
from functools import wraps

from synnefo.db.models import *
from synnefo.db import models_factory as mfactory

from synnefo.api import faults



@contextmanager
def astakos_user(user):
    """
    Context manager to mock astakos response.

    usage:
    with astakos_user("user@user.com"):
        .... make api calls ....

    """
    def dummy_get_user(request, *args, **kwargs):
        request.user = {'username': user, 'groups': []}
        request.user_uniq = user

    with patch('synnefo.api.util.get_user') as m:
        m.side_effect = dummy_get_user
        yield


class BaseAPITest(TestCase):
    def get(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.get(url, *args, **kwargs)
        return response

    def delete(self, url, user='user'):
        with astakos_user(user):
            response = self.client.delete(url)
        return response

    def post(self, url, user='user', params={}, ctype='json', *args, **kwargs):
        if ctype == 'json':
            content_type = 'application/json'
        with astakos_user(user):
            response = self.client.post(url, params, content_type=content_type,
                                        *args, **kwargs)
        return response

    def put(self, url, user='user', params={}, ctype='json', *args, **kwargs):
        if ctype == 'json':
            content_type = 'application/json'
        with astakos_user(user):
            response = self.client.put(url, params, content_type=content_type,
                    *args, **kwargs)
        return response

    def assertSuccess(self, response):
        self.assertTrue(response.status_code in [200, 203, 204])

    def assertFault(self, response, status_code, name):
        self.assertEqual(response.status_code, status_code)
        fault = json.loads(response.content)
        self.assertEqual(fault.keys(), [name])

    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest')

    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound')


class APITest(TestCase):
    def test_api_version(self):
        """Check API version."""
        with astakos_user('user'):
            response = self.client.get('/api/v1.1/')
        self.assertEqual(response.status_code, 200)
        api_version = json.loads(response.content)['version']
        self.assertEqual(api_version['id'], 'v1.1')
        self.assertEqual(api_version['status'], 'CURRENT')


# Import TestCases
from synnefo.api.test.servers import *
from synnefo.api.test.networks import *
from synnefo.api.test.flavors import *
from synnefo.api.test.images import *

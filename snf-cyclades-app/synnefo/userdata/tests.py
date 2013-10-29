# Copyright 2011 GRNET S.A. All rights reserved.
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
#

from django import http
from django.test import TransactionTestCase
from django.conf import settings
from django.test.client import Client
from django.core.urlresolvers import clear_url_caches
from django.utils import simplejson as json
from django.conf import settings
from django.core.urlresolvers import reverse
from mock import patch

from synnefo.userdata.models import *


def get_user_mock(request, *args, **kwargs):
    if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0000':
        request.user_uniq = 'test'
        request.user = {'id': 'id',
                        'username': 'username',
                        'uuid': 'test'}


class AaiClient(Client):

    def request(self, **request):
        # mock the astakos authentication function
        with patch("synnefo.userdata.rest.get_user",
                   new=get_user_mock):
            with patch("synnefo.userdata.views.get_user",
                       new=get_user_mock):
                request['HTTP_X_AUTH_TOKEN'] = '0000'
                return super(AaiClient, self).request(**request)


class TestRestViews(TransactionTestCase):

    fixtures = ['users']

    def setUp(self):
        settings.USERDATA_MAX_SSH_KEYS_PER_USER = 10

        settings.SKIP_SSH_VALIDATION = True
        self.client = AaiClient()
        self.user = 'test'
        self.keys_url = reverse('ui_keys_collection')

    def test_keys_collection_get(self):
        resp = self.client.get(self.keys_url)
        self.assertEqual(resp.content, "[]")

        PublicKeyPair.objects.create(user=self.user, name="key pair 1",
                content="content1")

        resp = self.client.get(self.keys_url)
        resp_list = json.loads(resp.content);
        exp_list = [{"content": "content1", "id": 1,
                    "uri": self.keys_url + "/1", "name": "key pair 1",
                    "fingerprint": "unknown fingerprint"}]
        self.assertEqual(resp_list, exp_list)

        PublicKeyPair.objects.create(user=self.user, name="key pair 2",
                content="content2")

        resp = self.client.get(self.keys_url)
        resp_list = json.loads(resp.content)
        exp_list = [{"content": "content1", "id": 1,
                     "uri": self.keys_url + "/1", "name": "key pair 1",
                     "fingerprint": "unknown fingerprint"},
                    {"content": "content2", "id": 2,
                     "uri": self.keys_url + "/2",
                     "name": "key pair 2",
                     "fingerprint": "unknown fingerprint"}]

        self.assertEqual(resp_list, exp_list)

    def test_keys_resourse_get(self):
        resp = self.client.get(self.keys_url + "/1")
        self.assertEqual(resp.status_code, 404)

        # create a public key
        PublicKeyPair.objects.create(user=self.user, name="key pair 1",
                content="content1")
        resp = self.client.get(self.keys_url + "/1")
        resp_dict = json.loads(resp.content);
        exp_dict = {"content": "content1", "id": 1,
                    "uri": self.keys_url + "/1", "name": "key pair 1",
                    "fingerprint": "unknown fingerprint"}
        self.assertEqual(resp_dict, exp_dict)

        # update
        resp = self.client.put(self.keys_url + "/1",
                               json.dumps({'name':'key pair 1 new name'}),
                               content_type='application/json')

        pk = PublicKeyPair.objects.get(pk=1)
        self.assertEqual(pk.name, "key pair 1 new name")

        # delete
        resp = self.client.delete(self.keys_url + "/1")
        self.assertEqual(PublicKeyPair.objects.count(), 0)

        resp = self.client.get(self.keys_url + "/1")
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(self.keys_url)
        self.assertEqual(resp.content, "[]")

        # test rest create
        resp = self.client.post(self.keys_url,
                                json.dumps({'name':'key pair 2',
                                            'content':"""key 2 content"""}),
                                content_type='application/json')
        self.assertEqual(PublicKeyPair.objects.count(), 1)
        pk = PublicKeyPair.objects.get()
        self.assertEqual(pk.name, "key pair 2")
        self.assertEqual(pk.content, "key 2 content")

    def test_generate_views(self):
        import base64

        # just test that
        resp = self.client.post(self.keys_url + "/generate")
        self.assertNotEqual(resp, "")

        data = json.loads(resp.content)
        self.assertEqual(data.has_key('private'), True)
        self.assertEqual(data.has_key('private'), True)

        # public key is base64 encoded
        base64.b64decode(data['public'].replace("ssh-rsa ",""))

        # remove header/footer
        private = "".join(data['private'].split("\n")[1:-1])

        # private key is base64 encoded
        base64.b64decode(private)

        new_key = PublicKeyPair()
        new_key.content = data['public']
        new_key.name = "new key"
        new_key.user = 'test'
        new_key.full_clean()
        new_key.save()

    def test_generate_limit(self):
        settings.USERDATA_MAX_SSH_KEYS_PER_USER = 1
        resp = self.client.post(self.keys_url,
                                json.dumps({'name':'key1',
                                            'content':"""key 1 content"""}),
                                content_type='application/json')
        genpath = self.keys_url + "/generate"
        r = self.client.post(genpath)
        assert isinstance(r, http.HttpResponseServerError)

    def test_invalid_data(self):
        resp = self.client.post(self.keys_url,
                                json.dumps({'content':"""key 2 content"""}),
                                content_type='application/json')

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content, """{"non_field_key": "__all__", "errors": """
                                       """{"name": ["This field cannot be blank."]}}""")

        settings.USERDATA_MAX_SSH_KEYS_PER_USER = 2

        # test ssh limit
        resp = self.client.post(self.keys_url,
                                json.dumps({'name':'key1',
                                            'content':"""key 1 content"""}),
                                content_type='application/json')
        resp = self.client.post(self.keys_url,
                                json.dumps({'name':'key1',
                                            'content':"""key 1 content"""}),
                                content_type='application/json')
        resp = self.client.post(self.keys_url,
                                json.dumps({'name':'key1',
                                            'content':"""key 1 content"""}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content, """{"non_field_key": "__all__", "errors": """
                                       """{"__all__": ["SSH keys limit exceeded."]}}""")


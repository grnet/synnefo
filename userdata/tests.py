"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.conf import settings
from django.test.client import Client
from django.core.urlresolvers import clear_url_caches
from django.utils import simplejson as json

from synnefo.userdata.models import User
from synnefo.userdata.models import *

class AaiClient(Client):

    def request(self, **request):
        request['HTTP_X_AUTH_TOKEN'] = '46e427d657b20defe352804f0eb6f8a2'
        return super(AaiClient, self).request(**request)

class TestRestViews(TestCase):

    fixtures = ['users']

    def setUp(self):
        settings.ROOT_URLCONF = 'synnefo.userdata.urls'
        clear_url_caches()
        self.client = AaiClient()
        self.user = User.objects.get(pk=1)

    def test_keys_collection_get(self):
        resp = self.client.get("/keys/")
        self.assertEqual(resp.content, "[]")

        PublicKeyPair.objects.create(user=self.user, name="key pair 1",
                content="content1")

        resp = self.client.get("/keys/")
        self.assertEqual(resp.content, """[{"content": "content1", "uri": "/keys/1/", "name": "key pair 1", "id": 1}]""")

        PublicKeyPair.objects.create(user=self.user, name="key pair 2",
                content="content2")

        resp = self.client.get("/keys/")
        self.assertEqual(resp.content, """[{"content": "content1", "uri": "/keys/1/", "name": "key pair 1", "id": 1}, {"content": "content2", "uri": "/keys/2/", "name": "key pair 2", "id": 2}]""")

    def test_keys_resourse_get(self):
        resp = self.client.get("/keys/1/")
        self.assertEqual(resp.status_code, 404)

        # create a public key
        PublicKeyPair.objects.create(user=self.user, name="key pair 1",
                content="content1")
        resp = self.client.get("/keys/1/")
        self.assertEqual(resp.content, """{"content": "content1", "uri": "/keys/1/", "name": "key pair 1", "id": 1}""")

        # update
        resp = self.client.post("/keys/1/", json.dumps({'name':'key pair 1 new name'}),
                content_type='application/json')
        pk = PublicKeyPair.objects.get(pk=1)
        self.assertEqual(pk.name, "key pair 1 new name")

        # delete
        resp = self.client.delete("/keys/1/")
        self.assertEqual(PublicKeyPair.objects.count(), 0)

        resp = self.client.get("/keys/1/")
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get("/keys/")
        self.assertEqual(resp.content, "[]")

"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.conf import settings
from django.test.client import Client
from django.core.urlresolvers import clear_url_caches

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
        self.assertEqual(resp.content, """[{"content": "content1", "id": 1, "name": "key pair 1"}]""")

        PublicKeyPair.objects.create(user=self.user, name="key pair 2",
                content="content2")

        resp = self.client.get("/keys/")
        self.assertEqual(resp.content, """[{"content": "content1", "id": 1, "name": "key pair 1"}, {"content": "content2", "id": 2, "name": "key pair 2"}]""")

    def test_keys_resourse_get(self):
        pass

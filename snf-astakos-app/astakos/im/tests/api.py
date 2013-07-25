# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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

from astakos.im.tests.common import *
from astakos.im.settings import astakos_services, BASE_HOST
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from django.test import TestCase
from django.core.urlresolvers import reverse

#from xml.dom import minidom

import json

ROOT = "/%s/%s/%s/" % (
    astakos_settings.BASE_PATH, astakos_settings.ACCOUNTS_PREFIX, 'v1.0')
u = lambda url: ROOT + url


class QuotaAPITest(TestCase):
    def test_0(self):
        client = Client()

        component1 = Component.objects.create(name="comp1")
        register.add_service(component1, "service1", "type1", [])
        # custom service resources
        resource11 = {"name": "service1.resource11",
                      "desc": "resource11 desc",
                      "service_type": "type1",
                      "service_origin": "service1",
                      "allow_in_projects": True}
        r, _ = register.add_resource(resource11)
        register.update_resource(r, 100)
        resource12 = {"name": "service1.resource12",
                      "desc": "resource11 desc",
                      "service_type": "type1",
                      "service_origin": "service1",
                      "unit": "bytes"}
        r, _ = register.add_resource(resource12)
        register.update_resource(r, 1024)

        # create user
        user = get_local_user('test@grnet.gr')
        quotas.qh_sync_user(user)

        component2 = Component.objects.create(name="comp2")
        register.add_service(component2, "service2", "type2", [])
        # create another service
        resource21 = {"name": "service2.resource21",
                      "desc": "resource11 desc",
                      "service_type": "type2",
                      "service_origin": "service2",
                      "allow_in_projects": False}
        r, _ = register.add_resource(resource21)
        register.update_resource(r, 3)

        resource_names = [r['name'] for r in
                          [resource11, resource12, resource21]]

        # get resources
        r = client.get(u('resources'))
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        for name in resource_names:
            assertIn(name, body)

        # get quota
        r = client.get(u('quotas'))
        self.assertEqual(r.status_code, 401)

        headers = {'HTTP_X_AUTH_TOKEN': user.auth_token}
        r = client.get(u('quotas/'), **headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        system_quota = body['system']
        assertIn('system', body)
        for name in resource_names:
            assertIn(name, system_quota)

        r = client.get(u('service_quotas'))
        self.assertEqual(r.status_code, 401)

        s1_headers = {'HTTP_X_AUTH_TOKEN': component1.auth_token}
        r = client.get(u('service_quotas'), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        assertIn(user.uuid, body)

        r = client.get(u('commissions'), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body, [])

        # issue some commissions
        commission_request = {
            "force": False,
            "auto_accept": False,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 30000
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 413)

        commission_request = {
            "force": False,
            "auto_accept": False,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        serial = body['serial']
        self.assertEqual(serial, 1)

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        self.assertEqual(body['serial'], 2)

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        self.assertEqual(body['serial'], 3)

        r = client.get(u('commissions'), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body, [1, 2, 3])

        r = client.get(u('commissions/' + str(serial)), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body['serial'], serial)
        assertIn('issue_time', body)
        self.assertEqual(body['provisions'], commission_request['provisions'])
        self.assertEqual(body['name'], commission_request['name'])

        r = client.get(u('service_quotas?user=' + user.uuid), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        user_quota = body[user.uuid]
        system_quota = user_quota['system']
        r11 = system_quota[resource11['name']]
        self.assertEqual(r11['usage'], 3)
        self.assertEqual(r11['pending'], 3)

        # resolve pending commissions
        resolve_data = {
            "accept": [1, 3],
            "reject": [2, 3, 4],
        }
        post_data = json.dumps(resolve_data)

        r = client.post(u('commissions/action'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body['accepted'], [1])
        self.assertEqual(body['rejected'], [2])
        failed = body['failed']
        self.assertEqual(len(failed), 2)

        r = client.get(u('commissions/' + str(serial)), **s1_headers)
        self.assertEqual(r.status_code, 404)

        # auto accept
        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        serial = body['serial']
        self.assertEqual(serial, 4)

        r = client.get(u('commissions/' + str(serial)), **s1_headers)
        self.assertEqual(r.status_code, 404)

        # malformed
        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                }
            ]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 400)

        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": "dummy"}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 400)

        r = client.post(u('commissions'), commission_request,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 400)

        # no holding
        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": "non existent",
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 404)

        # release
        commission_request = {
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": -1
                }
            ]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        serial = body['serial']

        accept_data = {'accept': ""}
        post_data = json.dumps(accept_data)
        r = client.post(u('commissions/' + str(serial) + '/action'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 200)

        reject_data = {'reject': ""}
        post_data = json.dumps(accept_data)
        r = client.post(u('commissions/' + str(serial) + '/action'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 404)

        # force
        commission_request = {
            "force": True,
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)

        commission_request = {
            "force": True,
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": -200
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 413)

        r = client.get(u('quotas'), **headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        system_quota = body['system']
        r11 = system_quota[resource11['name']]
        self.assertEqual(r11['usage'], 102)
        self.assertEqual(r11['pending'], 101)

        # Bad Request
        r = client.head(u('commissions'))
        self.assertEqual(r.status_code, 400)


class TokensApiTest(TestCase):
    def setUp(self):
        backend = activation_backends.get_backend()

        self.user1 = AstakosUser.objects.create(
            email='test1', email_verified=True, moderated=True,
            is_rejected=False)
        backend.activate_user(self.user1)
        assert self.user1.is_active is True

        self.user2 = AstakosUser.objects.create(
            email='test2', email_verified=True, moderated=True,
            is_rejected=False)
        backend.activate_user(self.user2)
        assert self.user2.is_active is True

        c1 = Component(name='component1', url='http://localhost/component1')
        c1.save()
        s1 = Service(component=c1, type='type1', name='service1')
        s1.save()
        e1 = Endpoint(service=s1)
        e1.save()
        e1.data.create(key='versionId', value='v1.0')
        e1.data.create(key='publicURL', value='http://localhost:8000/s1/v1.0')

        s2 = Service(component=c1, type='type2', name='service2')
        s2.save()
        e2 = Endpoint(service=s2)
        e2.save()
        e2.data.create(key='versionId', value='v1.0')
        e2.data.create(key='publicURL', value='http://localhost:8000/s2/v1.0')

        c2 = Component(name='component2', url='http://localhost/component2')
        c2.save()
        s3 = Service(component=c2, type='type3', name='service3')
        s3.save()
        e3 = Endpoint(service=s3)
        e3.save()
        e3.data.create(key='versionId', value='v2.0')
        e3.data.create(key='publicURL', value='http://localhost:8000/s3/v2.0')

    def test_authenticate(self):
        client = Client()

        # Check not allowed method
        url = reverse('astakos.api.tokens.authenticate')
        r = client.get(url, post_data={})
        self.assertEqual(r.status_code, 400)

        # check public mode
        r = client.post(url, CONTENT_LENGTH=0)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('application/json'))
        try:
            body = json.loads(r.content)
        except Exception, e:
            self.fail(e)
        self.assertTrue('token' not in body.get('access'))
        self.assertTrue('user' not in body.get('access'))
        self.assertTrue('serviceCatalog' in body.get('access'))

        # Check unsupported xml input
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """
            <?xml version="1.0" encoding="UTF-8"?>
                <auth xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns="http://docs.openstack.org/identity/api/v2.0"
                 tenantName="%s">
                  <passwordCredentials username="%s" password="%s"/>
                </auth>""" % (self.user1.uuid, self.user1.uuid,
                              self.user1.auth_token)
        r = client.post(url, post_data, content_type='application/xml')
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertEqual(body['badRequest']['message'],
                         "Unsupported Content-type: 'application/xml'")

        # Check malformed request: missing password
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"passwordCredentials":{"username":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.uuid, self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertTrue(body['badRequest']['message'].
                        startswith('Malformed request'))

        # Check malformed request: missing username
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"passwordCredentials":{"password":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.auth_token, self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertTrue(body['badRequest']['message'].
                        startswith('Malformed request'))

        # Check invalid pass
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"passwordCredentials":{"username":"%s",
                                                       "password":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.uuid, '', self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 401)
        body = json.loads(r.content)
        self.assertEqual(body['unauthorized']['message'],
                         'Invalid token')

        # Check inconsistent pass
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"passwordCredentials":{"username":"%s",
                                                       "password":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.uuid, self.user2.auth_token, self.user2.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 401)
        body = json.loads(r.content)
        self.assertEqual(body['unauthorized']['message'],
                         'Invalid credentials')

        # Check invalid json data
        url = reverse('astakos.api.tokens.authenticate')
        r = client.post(url, "not json", content_type='application/json')
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertEqual(body['badRequest']['message'], 'Invalid JSON data')

        # Check auth with token
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"token": {"id":"%s"},
                        "tenantName":"%s"}}""" % (
            self.user1.auth_token, self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('application/json'))
        try:
            body = json.loads(r.content)
        except Exception, e:
            self.fail(e)

        # Check malformed request: missing token
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"auth_token":{"id":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.auth_token, self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertTrue(body['badRequest']['message'].
                        startswith('Malformed request'))

        # Check bad request: inconsistent tenant
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"token":{"id":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.auth_token, self.user2.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertEqual(body['badRequest']['message'],
                         'Not conforming tenantName')

        # Check bad request: inconsistent tenant
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"token":{"id":"%s"},
                                "tenantName":""}}""" % (
            self.user1.auth_token)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 200)

        # Check successful json response
        url = reverse('astakos.api.tokens.authenticate')
        post_data = """{"auth":{"passwordCredentials":{"username":"%s",
                                                       "password":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.uuid, self.user1.auth_token, self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('application/json'))
        try:
            body = json.loads(r.content)
        except Exception, e:
            self.fail(e)

        try:
            token = body['access']['token']['id']
            user = body['access']['user']['id']
            service_catalog = body['access']['serviceCatalog']
        except KeyError:
            self.fail('Invalid response')

        self.assertEqual(token, self.user1.auth_token)
        self.assertEqual(user, self.user1.uuid)
        self.assertEqual(len(service_catalog), 3)

        # Check successful xml response
        url = reverse('astakos.api.tokens.authenticate')
        headers = {'HTTP_ACCEPT': 'application/xml'}
        post_data = """{"auth":{"passwordCredentials":{"username":"%s",
                                                       "password":"%s"},
                                "tenantName":"%s"}}""" % (
            self.user1.uuid, self.user1.auth_token, self.user1.uuid)
        r = client.post(url, post_data, content_type='application/json',
                        **headers)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('application/xml'))
#        try:
#            body = minidom.parseString(r.content)
#        except Exception, e:
#            self.fail(e)


class WrongPathAPITest(TestCase):
    def test_catch_wrong_account_paths(self, *args):
        path = get_service_path(astakos_services, 'account', 'v1.0')
        path = join_urls(BASE_HOST, path, 'nonexistent')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 400)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)

    def test_catch_wrong_identity_paths(self, *args):
        path = get_service_path(astakos_services, 'identity', 'v2.0')
        path = join_urls(BASE_HOST, path, 'nonexistent')
        response = self.client.get(path)
        self.assertEqual(response.status_code, 400)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)

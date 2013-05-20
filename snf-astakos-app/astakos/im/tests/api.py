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

from astakos.im.tests.common import *
from django.test import TestCase

ROOT = '/astakos/api/'
u = lambda url: ROOT + url


class QuotaAPITest(TestCase):
    def test_0(self):
        client = Client()
        # custom service resources
        service1 = Service.objects.create(
            name="service1", api_url="http://service1.api")
        resource11 = {"name": "service1.resource11",
                      "desc": "resource11 desc",
                      "allow_in_projects": True}
        r, _ = resources.add_resource(service1, resource11)
        resources.update_resource(r, 100)
        resource12 = {"name": "service1.resource12",
                      "desc": "resource11 desc",
                      "unit": "bytes"}
        r, _ = resources.add_resource(service1, resource12)
        resources.update_resource(r, 1024)

        # create user
        user = get_local_user('test@grnet.gr')
        quotas.qh_sync_user(user)

        # create another service
        service2 = Service.objects.create(
            name="service2", api_url="http://service2.api")
        resource21 = {"name": "service2.resource21",
                      "desc": "resource11 desc",
                      "allow_in_projects": False}
        r, _ = resources.add_resource(service2, resource21)
        resources.update_resource(r, 3)

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

        s1_headers = {'HTTP_X_AUTH_TOKEN': service1.auth_token}
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

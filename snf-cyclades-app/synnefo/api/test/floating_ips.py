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

import json

from snf_django.utils.testing import BaseAPITest, mocked_quotaholder
from synnefo.db.models import FloatingIP
from synnefo.db.models_factory import FloatingIPFactory, NetworkFactory


URL = "/api/v1.1/os-floating-ips"


class FloatingIPAPITest(BaseAPITest):
    def test_no_floating_ip(self):
        response = self.get(URL)
        self.assertSuccess(response)
        self.assertEqual(json.loads(response.content)["floating_ips"], [])

    def test_list_ips(self):
        ip = FloatingIPFactory(userid="user1")
        FloatingIPFactory(userid="user1", deleted=True)
        with mocked_quotaholder():
            response = self.get(URL, "user1")
        self.assertSuccess(response)
        api_ip = json.loads(response.content)["floating_ips"][0]
        self.assertEqual(api_ip,
                         {"instance_id": str(ip.machine.id), "ip": ip.ipv4,
                          "fixed_ip": None, "id": str(ip.id),  "pool":
                          str(ip.network.id)})

    def test_get_ip(self):
        ip = FloatingIPFactory(userid="user1")
        with mocked_quotaholder():
            response = self.get(URL + "/%s" % ip.id, "user1")
        self.assertSuccess(response)
        api_ip = json.loads(response.content)["floating_ip"]
        self.assertEqual(api_ip,
                         {"instance_id": str(ip.machine.id), "ip": ip.ipv4,
                          "fixed_ip": None, "id": str(ip.id),  "pool":
                          str(ip.network.id)})

    def test_wrong_user(self):
        ip = FloatingIPFactory(userid="user1")
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, "user2")
        self.assertItemNotFound(response)

    def test_deleted_ip(self):
        ip = FloatingIPFactory(userid="user1", deleted=True)
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, "user1")
        self.assertItemNotFound(response)

    def test_reserve(self):
        net = NetworkFactory(userid="test_user", subnet="192.168.2.0/24",
                             gateway=None, public=True)
        request = {'pool': net.id}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertSuccess(response)
        ip = FloatingIP.objects.get()
        self.assertEqual(ip.ipv4, "192.168.2.1")
        self.assertEqual(ip.machine, None)
        self.assertEqual(ip.network, net)
        self.assertEqual(json.loads(response.content)["floating_ip"],
                         {"instance_id": None, "ip": "192.168.2.1",
                          "fixed_ip": None, "id": "1", "pool": "1"})

    def test_reserve_full(self):
        net = NetworkFactory(userid="test_user", subnet="192.168.2.0/32",
                             gateway=None, public=True)
        request = {'pool': net.id}
        with mocked_quotaholder():
            response = self.post(URL, "test_user", json.dumps(request), "json")
        self.assertEqual(response.status_code, 413)

    def test_release_in_use(self):
        ip = FloatingIPFactory()
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertFault(response, 409, "conflict")

    def test_release(self):
        ip = FloatingIPFactory(machine=None)
        with mocked_quotaholder():
            response = self.delete(URL + "/%s" % ip.id, ip.userid)
        self.assertSuccess(response)
        ips_after = FloatingIP.objects.filter(id=ip.id)
        self.assertEqual(len(ips_after), 0)

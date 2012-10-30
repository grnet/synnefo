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

from django.test import TestCase, Client
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db import models

class AaiClient(Client):

    def request(self, **request):
        token = request.pop('user_token', '0000')
        if token:
            request['HTTP_X_AUTH_TOKEN'] = token
        return super(AaiClient, self).request(**request)

class HelpdeskTests(TestCase):
    """
    Helpdesk tests. Test correctness of permissions and returned data.
    """

    fixtures = ['helpdesk_test']

    def setUp(self):

        def get_user_mock(request, *args, **kwargs):
            if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0000':
                request.user_uniq = 'test'
                request.user = {'uniq': 'test'}
            if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0001':
                request.user_uniq = 'test'
                request.user = {'uniq': 'test', 'groups':['default','helpdesk']}

        # mock the astakos authentication function
        from synnefo.lib import astakos
        astakos.get_user = get_user_mock

        settings.SKIP_SSH_VALIDATION = True
        settings.HELPDESK_ENABLED = True
        self.client = AaiClient()
        self.user = 'test'
        self.keys_url = reverse('ui_keys_collection')

    def test_enabled_setting(self):
        settings.HELPDESK_ENABLED = False

        # helpdesk is disabled
        r = self.client.get(reverse('helpdesk-index'), user_token="0001")
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse('helpdesk-details', args=['testuser@test.com']),
                user_token="0001")
        self.assertEqual(r.status_code, 404)

    def test_ip_lookup(self):
        # ip does not exist, proper message gets displayed
        r = self.client.get(reverse('helpdesk-details',
            args=["195.251.221.122"]), user_token='0001')
        self.assertContains(r, 'User with IP')

        # ip exists, 'test' account discovered
        r = self.client.get(reverse('helpdesk-details',
            args=["195.251.222.211"]), user_token='0001')
        self.assertEqual(r.context['account'], 'testuser2@test.com')

    def test_view_permissions(self):

        # anonymous user gets 403
        r = self.client.get(reverse('helpdesk-index'), user_token=None)
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('helpdesk-details', args=['testuser@test.com']),
                user_token=None)
        self.assertEqual(r.status_code, 403)

        # user not in helpdesk group gets 403
        r = self.client.get(reverse('helpdesk-index'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('helpdesk-details', args=['testuser@test.com']))
        self.assertEqual(r.status_code, 403)

        # user with helpdesk group gets 200
        r = self.client.get(reverse('helpdesk-index'), user_token="0001")
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('helpdesk-details', args=['testuser@test.com']),
                user_token="0001")
        self.assertEqual(r.status_code, 200)

    def test_results_get_filtered(self):
        """
        Test that view context data are filtered based on userid provided.
        Check helpdesk_test.json to see the existing database data.
        """

        # 'testuser@test.com' details, see helpdes/fixtures/helpdesk_test.json for
        # more details
        r = self.client.get(reverse('helpdesk-details', args=['testuser@test.com']),
                user_token="0001")
        account = r.context['account']
        vms = r.context['vms']
        nets = r.context['networks']
        self.assertEqual(account, "testuser@test.com")
        self.assertEqual(vms[0].name, "user1 vm")
        self.assertEqual(vms.count(), 1)
        self.assertEqual(len(nets), 2)
        self.assertEqual(r.context['account_exists'], True)


        # 'testuser2@test.com' details, see helpdes/fixtures/helpdesk_test.json for
        # more details
        r = self.client.get(reverse('helpdesk-details', args=['testuser2@test.com']),
                user_token="0001")
        account = r.context['account']
        vms = r.context['vms']
        nets = r.context['networks']
        self.assertEqual(account, "testuser2@test.com")
        self.assertEqual(vms[0].name, "user2 vm1")
        self.assertEqual(vms[1].name, "user2 vm2")
        self.assertEqual(vms.count(), 2)
        self.assertEqual(len(nets), 1)
        self.assertEqual(r.context['account_exists'], True)

        # 'testuser5@test.com' does not exist, should be redirected to helpdesk home
        r = self.client.get(reverse('helpdesk-details', args=['testuser5@test.com']),
                user_token="0001")
        vms = r.context['vms']
        self.assertEqual(r.context['account_exists'], False)
        self.assertEqual(vms.count(), 0)
        # 1 public network
        self.assertEqual(len(nets), 1)
        self.assertEqual(r.context['account_exists'], False)

    def test_json_users(self):
        # invalid prefix gives 404 response
        r = self.client.get(reverse('helpdesk-userslist') + "?prefix=test",
                user_token="0001")
        self.assertEqual(r.status_code, 404)

        # no users exist
        r = self.client.get(reverse('helpdesk-userslist') + "?prefix=test@",
                user_token="0001")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, "[]")

        # 1 user exists
        r = self.client.get(reverse('helpdesk-userslist') + "?prefix=testuser@",
                user_token="0001")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '["testuser@test.com"]')
        r = self.client.get(reverse('helpdesk-userslist') + "?prefix=testuser@t",
                user_token="0001")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '["testuser@test.com"]')


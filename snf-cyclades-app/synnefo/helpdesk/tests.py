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

import mock

from django.test import TestCase, Client
from django.conf import settings
from django.core.urlresolvers import reverse


USER1 = "5edcb5aa-1111-4146-a8ed-2b6287824353"
USER2 = "5edcb5aa-2222-4146-a8ed-2b6287824353"

USERS_UUIDS = {}
USERS_UUIDS[USER1] = {'displayname': 'testuser@test.com'}
USERS_UUIDS[USER2] = {'displayname': 'testuser2@test.com'}

USERS_DISPLAYNAMES = dict(map(lambda k: (k[1]['displayname'], {'uuid': k[0]}),
                          USERS_UUIDS.iteritems()))

from synnefo.db import models_factory as mfactory


class AstakosClientMock():
    def __init__(*args, **kwargs):
        pass

    def get_username(self, token, uuid):
        try:
            return USERS_UUIDS.get(uuid)['displayname']
        except TypeError:
            return None

    def get_uuid(self, token, display_name):
        try:
            return USERS_DISPLAYNAMES.get(display_name)['uuid']
        except TypeError:
            return None


class AuthClient(Client):

    def request(self, **request):
        token = request.pop('user_token', '0000')
        if token:
            request['HTTP_X_AUTH_TOKEN'] = token
        return super(AuthClient, self).request(**request)


def get_user_mock(request, *args, **kwargs):
    request.user_uniq = None
    request.user = None
    if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0000':
        request.user_uniq = 'test'
        request.user = {'uniq': 'test', 'auth_token': '0000'}
    if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0001':
        request.user_uniq = 'test'
        request.user = {'uniq': 'test', 'groups': ['default',
                                                   'helpdesk'],
                        'auth_token': '0001'}


@mock.patch("astakosclient.AstakosClient", new=AstakosClientMock)
@mock.patch("snf_django.lib.astakos.get_user", new=get_user_mock)
class HelpdeskTests(TestCase):
    """
    Helpdesk tests. Test correctness of permissions and returned data.
    """

    def setUp(self):
        settings.SKIP_SSH_VALIDATION = True
        settings.HELPDESK_ENABLED = True
        self.client = AuthClient()

        # init models
        vm1u1 = mfactory.VirtualMachineFactory(userid=USER1, name="user1 vm",
                                               pk=1001)
        vm1u2 = mfactory.VirtualMachineFactory(userid=USER2, name="user2 vm1",
                                               pk=1002)
        vm2u2 = mfactory.VirtualMachineFactory(userid=USER2, name="user2 vm2",
                                               pk=1003)

        netpub = mfactory.NetworkFactory(public=True)
        net1u1 = mfactory.NetworkFactory(public=False, userid=USER1)

        nic1 = mfactory.NetworkInterfaceFactory(machine=vm1u2, network=net1u1)
        nic2 = mfactory.NetworkInterfaceFactory(machine=vm1u1, network=netpub,
                                                ipv4="195.251.222.211")

    def test_enabled_setting(self):
        settings.HELPDESK_ENABLED = False

        # helpdesk is disabled
        r = self.client.get(reverse('helpdesk-index'), user_token="0001")
        self.assertEqual(r.status_code, 404)
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
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
        self.assertEqual(r.context['account'], USER1)

    def test_vm_lookup(self):
        # vm id does not exist
        r = self.client.get(reverse('helpdesk-details',
                            args=["vm-123"]), user_token='0001')
        self.assertContains(r, 'User with Virtual Machine')

        # vm exists, 'test' account discovered
        r = self.client.get(reverse('helpdesk-details',
                            args=["vm1001"]), user_token='0001')
        self.assertEqual(r.context['account'], USER1)
        r = self.client.get(reverse('helpdesk-details',
                            args=["vm1002"]), user_token='0001')
        self.assertEqual(r.context['account'], USER2)
        # dash also works
        r = self.client.get(reverse('helpdesk-details',
                            args=["vm-1002"]), user_token='0001')
        self.assertEqual(r.context['account'], USER2)

    def test_view_permissions(self):
        # anonymous user gets 403
        r = self.client.get(reverse('helpdesk-index'), user_token=None)
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
                            user_token=None)
        self.assertEqual(r.status_code, 403)

        # user not in helpdesk group gets 403
        r = self.client.get(reverse('helpdesk-index'))
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']))
        self.assertEqual(r.status_code, 403)

        # user with helpdesk group gets 200
        r = self.client.get(reverse('helpdesk-index'), user_token="0001")
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
                            user_token="0001")
        self.assertEqual(r.status_code, 200)

        r = self.client.post(reverse('helpdesk-suspend-vm', args=(1001,)))
        r = self.client.get(reverse('helpdesk-suspend-vm', args=(1001,)),
                            user_token="0001", data={'token': '1234'})
        self.assertEqual(r.status_code, 403)
        r = self.client.get(reverse('helpdesk-suspend-vm', args=(1001,)),
                            user_token="0001")
        self.assertEqual(r.status_code, 403)
        r = self.client.post(reverse('helpdesk-suspend-vm', args=(1001,)),
                             user_token="0001", data={'token': '0001'})
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('helpdesk-suspend-vm', args=(1001,)),
                             user_token="0000", data={'token': '0000'})
        self.assertEqual(r.status_code, 403)

    def test_suspend_vm(self):
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
                            user_token="0001")
        self.assertEqual(r.status_code, 200)
        vmid = r.context['vms'][0].pk
        r = self.client.post(reverse('helpdesk-suspend-vm', args=(vmid,)),
                             data={'token': '0001'}, user_token="0001")
        self.assertEqual(r.status_code, 302)

        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
                            user_token="0001")
        self.assertTrue(r.context['vms'][0].suspended)

        r = self.client.post(reverse('helpdesk-suspend-vm-release',
                                     args=(vmid,)), data={'token': '0001'},
                             user_token="0001")
        self.assertEqual(r.status_code, 302)
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
                            user_token="0001")
        self.assertFalse(r.context['vms'][0].suspended)

    def test_results_get_filtered(self):
        """
        Test that view context data are filtered based on userid provided.
        Check helpdesk_test.json to see the existing database data.
        """

        # 'testuser@test.com' details, see
        # helpdes/fixtures/helpdesk_test.json for more details
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser@test.com']),
                            user_token="0001")
        account = r.context['account']
        vms = r.context['vms']
        nets = r.context['networks']
        self.assertEqual(account, USER1)
        self.assertEqual(vms[0].name, "user1 vm")
        self.assertEqual(vms.count(), 1)
        self.assertEqual(len(nets), 2)
        self.assertEqual(r.context['account_exists'], True)

        # 'testuser2@test.com' details, see helpdesk
        # /fixtures/helpdesk_test.json for more details
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser2@test.com']),
                            user_token="0001")
        account = r.context['account']
        vms = r.context['vms']
        nets = r.context['networks']
        self.assertEqual(account, USER2)
        self.assertEqual(vms.count(), 2)
        self.assertEqual(sorted([vms[0].name, vms[1].name]),
                         sorted(["user2 vm1", "user2 vm2"]))
        self.assertEqual(len(nets), 0)
        self.assertEqual(r.context['account_exists'], True)

        # 'testuser5@test.com' does not exist, should be redirected to
        # helpdesk home
        r = self.client.get(reverse('helpdesk-details',
                                    args=['testuser5@test.com']),
                            user_token="0001")
        vms = r.context['vms']
        self.assertEqual(r.context['account_exists'], False)
        self.assertEqual(vms.count(), 0)

    def test_start_shutdown(self):
        from synnefo.logic import backend

        self.vm1 = mfactory.VirtualMachineFactory(userid=USER1)
        pk = self.vm1.pk

        r = self.client.post(reverse('helpdesk-vm-shutdown', args=(pk,)))
        self.assertEqual(r.status_code, 403)

        r = self.client.post(reverse('helpdesk-vm-shutdown', args=(pk,)),
                             data={'token': '0001'})
        self.assertEqual(r.status_code, 403)

        backend.shutdown_instance = shutdown = mock.Mock()
        shutdown.return_value = 1
        self.vm1.operstate = 'STARTED'
        self.vm1.save()
        r = self.client.post(reverse('helpdesk-vm-shutdown', args=(pk,)),
                             data={'token': '0001'}, user_token='0001')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(shutdown.called)
        self.assertEqual(len(shutdown.mock_calls), 1)

        backend.startup_instance = startup = mock.Mock()
        startup.return_value = 2
        self.vm1.operstate = 'STOPPED'
        self.vm1.save()
        r = self.client.post(reverse('helpdesk-vm-start', args=(pk,)),
                             data={'token': '0001'}, user_token='0001')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(startup.called)
        self.assertEqual(len(startup.mock_calls), 1)

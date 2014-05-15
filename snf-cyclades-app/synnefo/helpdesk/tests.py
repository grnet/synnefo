# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from mock import patch
from django.test import TestCase, Client
from django.conf import settings
from django.core.urlresolvers import reverse
from snf_django.utils.testing import mocked_quotaholder


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

    def get_username(self, uuid):
        try:
            return USERS_UUIDS.get(uuid)['displayname']
        except TypeError:
            return None

    def get_uuid(self, display_name):
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
        request.user = {"access": {
                        "token": {
                            "expires": "2013-06-19T15:23:59.975572+00:00",
                            "id": "0000",
                            "tenant": {
                                "id": "test",
                                "name": "Firstname Lastname"
                                }
                            },
                        "serviceCatalog": [],
                        "user": {
                            "roles_links": [],
                            "id": "test",
                            "roles": [{"id": 1, "name": "default"}],
                            "name": "Firstname Lastname"}}
                        }

    if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0001':
        request.user_uniq = 'test'
        request.user = {"access": {
                        "token": {
                            "expires": "2013-06-19T15:23:59.975572+00:00",
                            "id": "0001",
                            "tenant": {
                                "id": "test",
                                "name": "Firstname Lastname"
                                }
                            },
                        "serviceCatalog": [],
                        "user": {
                            "roles_links": [],
                            "id": "test",
                            "roles": [{"id": 1, "name": "default"},
                                      {"id": 2, "name": "helpdesk"}],
                            "name": "Firstname Lastname"}}
                        }


@patch("astakosclient.AstakosClient", new=AstakosClientMock)
@patch("snf_django.lib.astakos.get_user", new=get_user_mock)
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

        nic1 = mfactory.NetworkInterfaceFactory(machine=vm1u2,
                                                userid=vm1u2.userid,
                                                network__public=False,
                                                network__userid=USER1)
        nic2 = mfactory.NetworkInterfaceFactory(machine=vm1u2,
                                                userid=vm1u2.userid,
                                                network__public=False,
                                                network__userid=USER1)
        ip2 = mfactory.IPv4AddressFactory(nic__machine=vm1u1,
                                          userid=vm1u1.userid,
                                          network__public=True,
                                          network__userid=None,
                                          address="195.251.222.211")
        ipv6 = mfactory.IPv4AddressFactory(nic__machine=vm1u1,
                                          userid=vm1u1.userid,
                                          network__public=True,
                                          network__userid=None,
                                          address="2001:648:2ffc:200::184")
        mfactory.IPAddressLogFactory(address=ip2.address,
                                     server_id=vm1u1.id,
                                     network_id=ip2.network.id,
                                     active=True)
        mfactory.IPAddressLogFactory(address=ipv6.address,
                                     server_id=vm1u1.id,
                                     network_id=ipv6.network.id,
                                     active=True)

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
        self.assertFalse(r.context["ip_exists"])
        self.assertEqual(list(r.context["ips"]), [])

        # ip exists
        r = self.client.get(reverse('helpdesk-details',
                            args=["195.251.222.211"]), user_token='0001')
        self.assertTrue(r.context["ip_exists"])
        ips = r.context["ips"]
        for ip in ips:
            self.assertEqual(ip.address, "195.251.222.211")

        # ipv6 matched
        r = self.client.get(reverse('helpdesk-details',
                                    args=["2001:648:2ffc:200::184"]),
                                    user_token='0001')
        self.assertTrue(r.context["ip_exists"])
        ips = r.context["ips"]
        for ip in ips:
            self.assertEqual(ip.address, "2001:648:2ffc:200::184")

        # ipv6 does not exist
        r = self.client.get(reverse('helpdesk-details',
                            args=["2001:648:2ffc:1225:a800:6ff:fe79:5de3"]),
                            user_token='0001')
        self.assertTrue(r.context["is_ip"])
        self.assertFalse(r.context["ip_exists"])

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
        self.assertEqual(len(nets), 4)
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
        self.vm1 = mfactory.VirtualMachineFactory(userid=USER1)
        pk = self.vm1.pk

        r = self.client.post(reverse('helpdesk-vm-shutdown', args=(pk,)))
        self.assertEqual(r.status_code, 403)

        r = self.client.post(reverse('helpdesk-vm-shutdown', args=(pk,)),
                             data={'token': '0001'})
        self.assertEqual(r.status_code, 403)

        self.vm1.operstate = 'STARTED'
        self.vm1.save()
        with patch("synnefo.logic.backend.shutdown_instance") as shutdown:
            shutdown.return_value = 1
            with mocked_quotaholder():
                r = self.client.post(
                    reverse('helpdesk-vm-shutdown', args=(pk,)),
                    data={'token': '0001'}, user_token='0001')
                self.assertEqual(r.status_code, 302)
                self.assertTrue(shutdown.called)
                self.assertEqual(len(shutdown.mock_calls), 1)

        self.vm1.operstate = 'STOPPED'
        self.vm1.save()
        with patch("synnefo.logic.backend.startup_instance") as startup:
            startup.return_value = 2
            with mocked_quotaholder():
                r = self.client.post(reverse('helpdesk-vm-start', args=(pk,)),
                                     data={'token': '0001'}, user_token='0001')
                self.assertEqual(r.status_code, 302)
                self.assertTrue(startup.called)
                self.assertEqual(len(startup.mock_calls), 1)

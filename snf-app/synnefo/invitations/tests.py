# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
from datetime import datetime, timedelta

from django.test import TestCase
from django.test.client import Client

import invitations
from synnefo.db.models import SynnefoUser, Invitations
from django.conf import settings


class InvitationsTestCase(TestCase):
    fixtures = ['users']
    token = settings.BYPASS_AUTHENTICATION_SECRET_TOKEN

    def setUp(self):
        self.client = Client()

    def test_add_invitation(self):
        """
            Tests whether invitations can be added
        """
        inv = self._add_invitation()
        source = inv.source

        # Re-adding an existing invitation
        try:
            invitations.add_invitation(source, u'', "test@gmail.com")
            self.assertTrue(False)
        except invitations.AlreadyInvited:
            self.assertTrue(True)
        except Exception:
            self.assertTrue(False)

        # Hit the invitation limit
        try:
            source.max_invitations = 0
            source.save()
            self._add_invitation()
        except invitations.TooManyInvitations:
            self.assertTrue(True)
        except Exception:
            self.assertTrue(False)

    def test_get_invitee_level(self):
        """
            Checks whether invitation levels and their limits are being respected
        """
        source = SynnefoUser.objects.filter(auth_token = self.token)[0]

        self.assertEqual(invitations.get_user_inv_level(source), -1)

        inv = invitations.add_invitation(source, "Test", "test@gmail.com")
        self.assertEqual(inv.target.max_invitations,
                         settings.INVITATIONS_PER_LEVEL[0])
        self.assertEqual(invitations.get_user_inv_level(inv.target), 0)

        inv = invitations.add_invitation(inv.target, "Test2", "test2@gmail.com")
        self.assertEqual(invitations.get_user_inv_level(inv.target), 1)
        self.assertEqual(inv.target.max_invitations,
                         settings.INVITATIONS_PER_LEVEL[1])

    def test_invitation_login(self):
        """
            Basic login by invitation checks
        """
        inv = self._add_invitation()
        user = inv.target

        url = invitations.enconde_inv_url(inv)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp['X-Auth-Token'], user.auth_token)

        # Invalid login url
        url = list(url)
        url[35] = '@'
        resp = self.client.get("".join(url))
        self.assertEqual(resp.status_code, 404)

    def test_relogin_with_expired_token(self):
        """
            Checks whether a user can login when his auth token has expired
        """
        inv = self._add_invitation()
        user = inv.target

        # Expire the user's token
        user.auth_token_expires = datetime.now()
        user.save()

        url = invitations.enconde_inv_url(inv)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp['X-Auth-Token'], user.auth_token)

        user = SynnefoUser.objects.get(uniq = "test@gmail.com")
        self.assertTrue(user.auth_token_expires > datetime.now())

        # Invitation valid less than max allowed auth token expiration time
        valid = timedelta(days = (settings.INVITATION_VALID_DAYS - 10))
        inv.created = inv.created - valid
        inv.save()

        user.auth_token_expires = datetime.now()
        user.save()

        url = invitations.enconde_inv_url(inv)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        inv = Invitations.objects.filter(target = user)[0]
        valid = timedelta(days = settings.INVITATION_VALID_DAYS)
        self.assertTrue(inv.created + valid >= user.auth_token_expires)

    def test_remove_invitation(self):
        """
        Tests the remove invitation method
        """
        inv = self._add_invitation()

        try:
            invitations.remove_invitation(inv)
            user = SynnefoUser.objects.filter(uniq = 'test@gmail.com').count()
            self.assertEquals(user, 0)

            inv = Invitations.objects.filter(target = user).count()
            self.assertEquals(inv, 0)
        except Exception:
            self.assertTrue(False)

        try:
            invitation = "Invitation"
            invitations.remove_invitation(inv)
        except Exception:
            self.assertTrue(False)

    def test_resend_invitation(self):
        """
        Tests the resend invitation method
        """
        inv = self._add_invitation()

        resp = self.client.post("/invitations/resend",
                                {'invid':inv.id},
                                **{'HTTP_X_AUTH_TOKEN': self.token})
        self.assertEquals(resp.status_code, 200)


        resp = self.client.post("/invitations/resend",
                                {'invid':'1;delete from db_invitations;'},
                                **{'HTTP_X_AUTH_TOKEN': self.token})
        self.assertEquals(resp.status_code, 400)

        resp = self.client.post("/invitations/resend",
                                {'invid':inv.id},
                                **{'HTTP_X_AUTH_TOKEN': inv.target.auth_token})
        self.assertEquals(resp.status_code, 400)

    def _add_invitation(self):
        source = SynnefoUser.objects.filter(auth_token = self.token)[0]
        invitations.add_invitation(source, "Test", "test@gmail.com")

        # Check whether the invited user has been added to the database
        user = SynnefoUser.objects.get(uniq = "test@gmail.com")

        self.assertNotEquals(user, None)
        self.assertEqual(user.uniq, 'test@gmail.com')

        inv = Invitations.objects.filter(target = user)[0]
        self.assertNotEquals(inv, None)

        return inv

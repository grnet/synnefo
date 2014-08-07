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

from django.core import mail

from astakos.im.user_logic import verify

from .common import SynnefoManagementTestCase, call_synnefo_command


def snf_manage(user, **kwargs):
    """An easy to use wrapper that simulates snf-manage."""
    id = str(user.pk)
    return call_synnefo_command("user-activation-send", *(id,), **kwargs)


class TestSendUserActivation(SynnefoManagementTestCase):

    """Class to unit test the "user-activation-send" management command."""

    def test_send_activation(self):
        """Test if verification mail is send appropriately."""
        # Sending a verification mail to an unverified user should work.
        out, err = snf_manage(self.user1)
        self.reload_user()
        self.assertInLog("Activation sent to '%s'" % self.user1.email, err)

        # Check if email is actually sent.
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn(self.user1.realname, body)
        self.assertIn(self.user1.verification_code, body)

        # Verify the user.
        self.assertEqual(len(mail.outbox), 1)
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # Sending a verification mail to a verified user should fail.
        out, err = snf_manage(self.user1)
        self.assertInLog("User email already verified '%s'" % self.user1.email,
                         err)

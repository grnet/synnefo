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

from django.test import TestCase
from astakos.im.user_logic import (validate_user_action, verify, accept,
                                   activate, deactivate, reject,
                                   send_verification_mail)
from astakos.im.auth import make_local_user
from astakos.im.models import AstakosUser
from snf_django.lib.api import faults
from django.core import mail


class TestUserActions(TestCase):

    """Testing various actions on user."""

    def setUp(self):
        """Common setup method for this test suite."""
        self.user1 = make_local_user("user1@synnefo.org")

    def tearDown(self):
        """Common teardown method for this test suite."""
        AstakosUser.objects.all().delete()

    def test_verify(self):
        """Test verification logic."""
        # Test if check function works properly for unverified user.
        ok, _ = validate_user_action(self.user1, "VERIFY", 'badc0d3')
        self.assertFalse(ok)
        ok, _ = validate_user_action(self.user1, "VERIFY",
                                     self.user1.verification_code)
        self.assertTrue(ok)

        # Test if verify action works properly for unverified user.
        res = verify(self.user1, 'badc0d3')
        self.assertTrue(res.is_error())
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())
        self.assertEqual(len(mail.outbox), 0)

        # Test if check function fails properly for verified user.
        ok, _ = validate_user_action(self.user1, "VERIFY", 'badc0d3')
        self.assertFalse(ok)
        ok, _ = validate_user_action(self.user1, "VERIFY",
                                     self.user1.verification_code)
        self.assertFalse(ok)

        # Test if verify action fails properly for verified user.
        res = verify(self.user1, 'badc0d3')
        self.assertTrue(res.is_error())
        res = verify(self.user1, self.user1.verification_code)
        self.assertTrue(res.is_error())
        self.assertEqual(len(mail.outbox), 0)

    def test_accept(self):
        """Test acceptance logic."""
        # Verify the user first.
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # Test if check function works properly for unmoderated user.
        ok, _ = validate_user_action(self.user1, "ACCEPT")
        self.assertTrue(ok)

        # Test if accept action works properly for unmoderated user.
        res = accept(self.user1)
        self.assertFalse(res.is_error())
        self.assertEqual(len(mail.outbox), 1)

        # Test if check function fails properly for moderated user.
        ok, _ = validate_user_action(self.user1, "ACCEPT")
        self.assertFalse(ok)

        # Test if accept action fails properly for moderated user.
        res = accept(self.user1)
        self.assertTrue(res.is_error())
        self.assertEqual(len(mail.outbox), 1)

        # Test if the rest of the actions can apply on a moderated user.
        # User cannot be rejected.
        ok, _ = validate_user_action(self.user1, "REJECT")
        self.assertFalse(ok)
        res = reject(self.user1, 'Too late')
        self.assertTrue(res.is_error())

        # User cannot be reactivated.
        ok, _ = validate_user_action(self.user1, "ACTIVATE")
        self.assertFalse(ok)
        res = activate(self.user1)
        self.assertTrue(res.is_error())

    def test_rejection(self):
        """Test if rejections are handled properly."""
        # Verify the user first.
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # Check rejection.
        ok, _ = validate_user_action(self.user1, "REJECT")
        self.assertTrue(ok)
        res = reject(self.user1, reason="Because")
        self.assertFalse(res.is_error())
        self.assertEqual(len(mail.outbox), 0)

        # Check if reason has been registered.
        self.assertEqual(self.user1.rejected_reason, "Because")

        # We cannot reject twice.
        ok, _ = validate_user_action(self.user1, "REJECT")
        self.assertFalse(ok)
        res = reject(self.user1, reason="Because")
        self.assertTrue(res.is_error())
        self.assertEqual(len(mail.outbox), 0)

        # We cannot deactivate a rejected user.
        ok, _ = validate_user_action(self.user1, "DEACTIVATE")
        self.assertFalse(ok)
        res = deactivate(self.user1)
        self.assertTrue(res.is_error())

        # We can, however, accept a rejected user.
        ok, msg = validate_user_action(self.user1, "ACCEPT")
        self.assertTrue(ok)

        # Test if accept action works on rejected users.
        res = accept(self.user1)
        self.assertFalse(res.is_error())
        self.assertEqual(len(mail.outbox), 1)

    def test_reactivation(self):
        """Test activation/deactivation logic."""
        # Verify the user.
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # We cannot deactivate an unmoderated user.
        ok, _ = validate_user_action(self.user1, "DEACTIVATE")
        self.assertFalse(ok)
        res = deactivate(self.user1)
        self.assertTrue(res.is_error())

        # Accept the user.
        res = accept(self.user1)
        self.assertFalse(res.is_error())

        # Check if we can deactivate properly an active user.
        ok, _ = validate_user_action(self.user1, "DEACTIVATE")
        self.assertTrue(ok)
        res = deactivate(self.user1)
        self.assertFalse(res.is_error())
        # This should be able to happen many times.
        ok, _ = validate_user_action(self.user1, "DEACTIVATE")
        self.assertTrue(ok)
        res = deactivate(self.user1)
        self.assertFalse(res.is_error())

        # Check if we can activate properly an inactive user
        ok, _ = validate_user_action(self.user1, "ACTIVATE")
        self.assertTrue(ok)
        res = activate(self.user1)
        self.assertFalse(res.is_error())
        # This should be able to happen only once.
        ok, _ = validate_user_action(self.user1, "ACTIVATE")
        self.assertFalse(ok)
        res = activate(self.user1)
        self.assertTrue(res.is_error())

    def test_exceptions(self):
        """Test if exceptions are raised properly."""
        # For an unverified user, run validate_user_action and check if
        # NotAllowed is raised for accept, activate, reject.
        for action in ("ACCEPT", "ACTIVATE", "REJECT"):
            with self.assertRaises(faults.NotAllowed) as cm:
                validate_user_action(self.user1, action, silent=False)
            self.assertEqual(cm.exception.message,
                             "Action %s is not allowed." % action)

        # Check if BadRequest is raised for a malformed action name.
        with self.assertRaises(faults.BadRequest) as cm:
            validate_user_action(self.user1, "BAD_ACTION", silent=False)
        self.assertEqual(cm.exception.message, "Unknown action: BAD_ACTION.")

    def test_verification_mail(self):
        """Test if verification mails are sent correctly."""
        # Check if we can send a verification mail to an unverified user.
        ok, _ = validate_user_action(self.user1, "SEND_VERIFICATION_MAIL")
        self.assertTrue(ok)
        send_verification_mail(self.user1)

        # Check if any mail has been sent and if so, check if it has two
        # important properties: the user's realname and his/her verification
        # code
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn(self.user1.realname, body)
        self.assertIn(self.user1.verification_code, body)

        # Verify the user.
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # Check if we are prevented from sending a verification mail.
        ok, _ = validate_user_action(self.user1, "SEND_VERIFICATION_MAIL")
        self.assertFalse(ok)
        with self.assertRaises(Exception) as cm:
            send_verification_mail(self.user1)
        self.assertEqual(cm.exception.message, "User email already verified.")

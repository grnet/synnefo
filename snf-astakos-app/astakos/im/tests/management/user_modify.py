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


from astakos.im.user_logic import (verify, accept, deactivate,)

from .common import SynnefoManagementTestCase, call_synnefo_command

actions = {
    "reject": {"reject": True},
    "verify": {"verify": True},
    "accept": {"accept": True},
    "activate": {"active": True},
    "deactivate": {"inactive": True},
}


def snf_manage(user, action, **kwargs):
    """An easy to use wrapper that simulates snf-manage."""
    kwargs.update(actions[action])
    id = str(user.pk)
    return call_synnefo_command("user-modify", *(id,), **kwargs)


class TestUserModification(SynnefoManagementTestCase):

    """Class to unit test the functionality of "user-modify"."""

    def test_verify(self):
        """Test verification option."""
        # Verifying the user should work.
        out, err = snf_manage(self.user1, "verify")
        self.assertInLog("Account verified", err)

        # Verifying the user again should fail.
        out, err = snf_manage(self.user1, "verify")
        self.assertInLog("Failed to verify", err)

    def test_accept(self):
        """Test accept option."""
        # Verify the user first.
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # Accepting the user should work.
        out, err = snf_manage(self.user1, "accept")
        self.assertInLog("Account accepted and activated", err)

        # Accepting the user again should fail.
        out, err = snf_manage(self.user1, "accept")
        self.assertInLog("Failed to accept", err)

    def test_reject(self):
        """Test reject option."""
        # Verify the user first
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())

        # Rejecting the user should work.
        out, err = snf_manage(self.user1, "reject", reject_reason="Because")
        self.assertInLog("Account rejected", err)
        self.reload_user()
        self.assertEqual(self.user1.rejected_reason, "Because")

        # Rejecting the user again should fail.
        out, err = snf_manage(self.user1, "reject",
                              reject_reason="Oops, I did it again")
        self.assertInLog("Failed to reject", err)
        self.reload_user()
        self.assertEqual(self.user1.rejected_reason, "Because")

    def test_deactivate(self):
        """Test deactivate option."""
        # Verify and accept the user first
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())
        res = accept(self.user1)
        self.assertFalse(res.is_error())

        # Deactivating the user should work.
        out, err = snf_manage(self.user1, "deactivate",
                              inactive_reason="Because")
        self.assertInLog("Account %s deactivated" % self.user1.username, err)
        self.reload_user()
        self.assertEqual(self.user1.deactivated_reason, "Because")

        # Deactivating the user again should also work.
        out, err = snf_manage(self.user1, "deactivate",
                              inactive_reason="Oops, I did it again")
        self.assertInLog("Account %s deactivated" % self.user1.username, err)
        self.reload_user()
        self.assertEqual(self.user1.deactivated_reason, "Oops, I did it again")

    def test_reactivate(self):
        """Test activate option."""
        # Verify and accept the user first
        res = verify(self.user1, self.user1.verification_code)
        self.assertFalse(res.is_error())
        res = accept(self.user1)
        self.assertFalse(res.is_error())

        # Activating the user should fail.
        out, err = snf_manage(self.user1, "activate")
        self.assertInLog("Failed to activate", err)

        # Deactivate the user in order to reactivate him/her.
        res = deactivate(self.user1)
        self.assertFalse(res.is_error())

        # Activating the user should work.
        out, err = snf_manage(self.user1, "activate")
        self.assertInLog("Account %s activated" % self.user1.username, err)

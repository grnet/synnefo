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

from StringIO import StringIO

from django.test import TestCase
from django.core.management import call_command

# Django has tests on user-defined management commands, which should be a good
# guide for our tests.
#
# These tests can be found here:
# https://github.com/django/django/blob/master/tests/user_commands/tests.py

from astakos.im.auth import make_local_user
from astakos.im.models import AstakosUser


class SynnefoManagementTestCase(TestCase):

    """Base class for testing synnefo management commands.

    This class provides a few useful assertions and functions that should aid
    in the testing of management commands.
    """

    def assertInLog(self, message, log):
        """Assert if log has a string."""
        self.assertIn(message, log.getvalue())

    def assertEmptyLog(self, log):
        """Assert if log is empty."""
        self.assertEqual(log.getvalue(), "")

    def setUp(self):
        """Common setup method for this test suite."""
        self.user1 = make_local_user("user1@synnefo.org")

    def tearDown(self):
        """Common teardown method for this test suite."""
        AstakosUser.objects.all().delete()

    def reload_user(self):
        """Reload a cached user instance from the DB.

        Model instances are cached, which means that if we get an instance
        of a model and the model gets updated via other means, our instance's
        fields will not change.

        The proposed solution is to fetch again the user from the database.

        For more info about this (common) scenario, see this ticket:

            https://code.djangoproject.com/ticket/901
        """
        self.user1 = AstakosUser.objects.get(pk=self.user1.pk)


def call_synnefo_command(command, *args, **options):
    """Wrapper over Django's `call_command`.

    Its main purpose is to call a command and return its output (stdout,
    stderr).
    """
    out = StringIO()
    err = StringIO()
    # Despite calling it from script, a management command may throw a
    # SystemExit exception. This exception can be ignored safely.
    #
    # Note: This has ben fixed in Django 1.5 (see Changelog).
    try:
        call_command(command, *args, stdout=out, stderr=err, **options)
    except SystemExit:
        pass
    return out, err

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

from django.db import transaction as django_transaction
from django.test import TransactionTestCase
from django.conf import settings

from astakos.im.models import AstakosUser
from astakos.im import transaction as astakos_transaction
from astakos.im.auth import make_local_user


class TransactionException(Exception):

    """A dummy exception specifically for the transaction tests."""

    pass


class TransactionTest(TransactionTestCase):

    """Check if astakos transactions work properly.

    TODO: Add multi-db tests.
    """

    def good_transaction(self):
        make_local_user("d@m.my")

    def bad_transaction(self):
        self.good_transaction()
        raise TransactionException

    def test_good_transaction(self):
        django_transaction.commit_on_success(self.good_transaction)()
        self.assertEqual(AstakosUser.objects.count(), 1)

    def test_bad_transaction(self):
        with self.assertRaises(TransactionException):
            django_transaction.commit_on_success(self.bad_transaction)()
        self.assertEqual(AstakosUser.objects.count(), 0)

    def test_good_transaction_custom_decorator(self):
        astakos_transaction.commit_on_success(self.good_transaction)()
        self.assertEqual(AstakosUser.objects.count(), 1)

    def test_bad_transaction_custom_decorator(self):
        with self.assertRaises(TransactionException):
            astakos_transaction.commit_on_success(self.bad_transaction)()
        self.assertEqual(AstakosUser.objects.count(), 0)

    def test_bad_transaction_custom_decorator_incorrect_dbs(self):
        settings.DATABASES['astakos'] = settings.DATABASES['default']
        with self.assertRaises(TransactionException):
            astakos_transaction.commit_on_success(self.bad_transaction)()
        self.assertEqual(AstakosUser.objects.count(), 0)
        settings.DATABASES.pop("astakos")

    def test_bad_transaction_custom_decorator_using(self):
        with self.assertRaises(TransactionException):
            astakos_transaction.commit_on_success(using="default")(self.bad_transaction)()
        self.assertEqual(AstakosUser.objects.count(), 0)

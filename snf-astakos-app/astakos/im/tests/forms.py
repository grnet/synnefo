# Copyright (C) 2010-2016 GRNET S.A.
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
from django import forms

from astakos.im.forms import EmailChangeForm
from astakos.im.fields import EmailField
from astakos.im.auth import make_local_user
from astakos.im.models import EmailChange

from mock import patch

class EmailChangeFormTest(TestCase):
    def test_form_contains_fields(self):
        form = EmailChangeForm()
        fields = {'new_email_address': EmailField}

        for field in form.fields.iterkeys():
            self.assertTrue(field in fields.iterkeys())
            self.assertTrue(isinstance(form.fields[field], fields[field]))

    @patch('astakos.im.forms.reserved_verified_email')
    def test_is_valid_with_clean_error(self, reserved_verified_email_mock):
        """ The `clean_email_address` method will use
        the `reserved_verified_email` function to check
        whether the new email is valid. If not it will
        raise a `forms.ValidationError` exception,
        so the form won't be valid
        """

        new_email_address = 'something@example.com'
        form = EmailChangeForm({'new_email_address': new_email_address})

        reserved_verified_email_mock.return_value = True
        self.assertFalse(form.is_valid())

    @patch('astakos.im.forms.reserved_verified_email')
    def test_is_valid_without_clean_error(self, reserved_verified_email_mock):
        new_email_address = 'something@example.com'
        form = EmailChangeForm({'new_email_address': new_email_address})

        reserved_verified_email_mock.return_value = False
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['new_email_address'], new_email_address)

    def create_email_change_for_user(self, user, new_email):
        return EmailChange.objects.create(
            user=user,
            new_email_address=new_email
        )

    def test_save(self):
        """ `save` should raise a `NotImplemented` exception
        """
        form = EmailChangeForm()
        with self.assertRaises(NotImplementedError):
            form.save()

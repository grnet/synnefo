# -*- coding: utf-8 -*-
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

from mock import patch

from django.test import TestCase
from django.core import mail
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError

from synnefo_branding.utils import render_to_string
from astakos.im import settings as astakos_settings
from astakos.im.models import AstakosUser, EmailChange
from astakos.im.user_utils import send_plain, change_user_email
from astakos.im.auth import make_local_user
import astakos.im.messages as astakos_messages
from astakos.im.tests.common import get_local_user


class TestUserUtils(TestCase):

    """Unit testing of various astakos user utilities."""

    def setUp(self):
        """Common setup method for this test suite."""
        self.user1 = make_local_user("user1@synnefo.org")

    def tearDown(self):
        """Common teardown method for this test suite."""
        AstakosUser.objects.all().delete()

    def test_send_plain_email(self):
        """Test if send_plain_email function works as intended."""
        def verify_sent_email(email_dict, mail):
            """Helper function to verify that an email was sent properly."""
            sender = email_dict.get('sender', astakos_settings.SERVER_EMAIL)
            subject = email_dict.get('subject',
                                     _(astakos_messages.PLAIN_EMAIL_SUBJECT))
            self.assertEqual(sender, mail.from_email)
            self.assertEqual(subject, mail.subject)
            self.assertEqual(email_dict['text'], mail.body)

        # Common variables
        template_name = 'im/plain_email.txt'
        text = u"Δεσποινίς, που είναι η μπάλα; Ümlaut.)?"
        expected_text = render_to_string(template_name, {
            'user': self.user1,
            'text': text,
            'baseurl': astakos_settings.BASE_URL,
            'support': astakos_settings.CONTACT_EMAIL})

        # Test 1 - Check if a simple test mail is sent properly.
        send_plain(self.user1, text=text)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertEqual(expected_text, body)

        # Test 2 - Check if the email template can get overriden.
        email_dict = {
            'template_name': None,
            'text': expected_text,
        }

        send_plain(self.user1, **email_dict)
        self.assertEqual(len(mail.outbox), 2)
        verify_sent_email(email_dict, mail.outbox[1])

        # Test 3 - Check if the email subject can get overriden.
        email_dict.update({'subject': u"Το θέμα μας είναι: Ümlaut."})
        send_plain(self.user1, **email_dict)
        self.assertEqual(len(mail.outbox), 3)
        verify_sent_email(email_dict, mail.outbox[2])

        # Test 4 - Check if the email sender can get overriden.
        email_dict.update({'sender': "someone@synnefo.org"})
        send_plain(self.user1, **email_dict)
        self.assertEqual(len(mail.outbox), 4)
        verify_sent_email(email_dict, mail.outbox[3])

    @patch('astakos.im.user_utils.send_change_email')
    def test_change_user_email(self, send_change_email_mock):
        """
        The `change_user_email` method should check if the email
        provided is valid. If it is invalid it should raise a
        `ValidationError` exception. Otherwise it should create
        an `EmailChange` instance on the database and call
        `send_change_email` with the email template provided.
        """
        user = get_local_user('something@something.com')

        # invalid new_email
        new_email = 'something.com'

        with self.assertRaises(ValidationError):
            change_user_email(user, new_email)

        # valid `new_email`, default `email_template_name`
        new_email = 'something@somethingelse.com'
        default_template = 'registration/email_change_email.txt'

        change_user_email(user, new_email)

        email_change = EmailChange.objects.get(new_email_address=new_email)
        send_change_email_mock.assert_called_once_with(email_change, default_template)
        self.assertTrue(user.email_change_is_pending())
        self.assertEqual(user.emailchanges.count(), 1)

        # valid mail, different `email_template_name`
        template = 'mytemplate/template.txt'
        change_user_email(user, new_email, email_template_name=template)

        email_change = EmailChange.objects.get(new_email_address=new_email)
        send_change_email_mock.assert_called_with(email_change, template)

        # the previous email change was deleted
        self.assertEqual(user.emailchanges.count(), 1)
        self.assertEqual(email_change, user.emailchanges.all()[0])

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

import unittest
import sys

from django.core import mail
from django.conf import settings

from synnefo.db import models_factory as mf
from astakos.im import settings as astakos_settings
from snf_django.lib.api import faults
from snf_django.utils.testing import override_settings
from synnefo.util.units import PRACTICALLY_INFINITE

from synnefo_admin import admin_settings
from synnefo_admin.admin import views
from synnefo_admin.admin import utils
from synnefo_admin.admin.exceptions import AdminHttp404
from .common import for_all_views, AdminTestCase, gibberish

model_views = admin_settings.ADMIN_VIEWS.copy()
# Remove the model views that do not have details
model_views.pop('ip_log', None)
model_views.pop('group', None)


class MockUser(object):
    realname = log_display = "Spider Jerusalem"
    first_name = "Spider"
    last_name = "Jerusalem"
    email = "thetruth@thehole.com"


class MockRequest(object):

    """Mock a Django request."""

    def __init__(self, content):
        self.POST = content

    def update(self, content):
        self.POST.update(content)


class MockResource(object):

    def __init__(self, unit):
        self.unit = unit


def reload_settings():
    """Reload admin settings after a Django setting has changed."""
    reload(sys.modules['synnefo_admin.admin_settings'])


class TestAdminUtilsUnit(unittest.TestCase):

    """Unit test suite for admin utility functions."""

    def test_render_email(self):
        """Test if emails are rendered properly."""
        user = MockUser()

        # Test 1 - Check if reqular emails are returned properly
        request = {
            "subject": "Very confidential",
            "text": "This is a very confidential mail",
        }

        subject, body = utils.render_email(user, request)
        self.assertEqual(request["subject"], subject)
        self.assertEqual(request["text"], body)

        # Test 2 - Check if emails with parameters are formatted properly
        subject = """Very confidential for {{ first_name }}
        {{ last_name }} or {{ full_name }} ({{ email }})"""
        body = """This is a very confidential mail for {{ first_name }}
        {{ last_name }} or {{ full_name }} ({{ email }})"""

        expected_subject = """Very confidential for Spider
        Jerusalem or Spider Jerusalem (thetruth@thehole.com)"""
        expected_body = """This is a very confidential mail for Spider
        Jerusalem or Spider Jerusalem (thetruth@thehole.com)"""

        request = {
            "subject": subject,
            "text": body,
        }

        subject, body = utils.render_email(user, request)
        self.assertEqual(expected_subject, subject)
        self.assertEqual(expected_body, body)

    def test_send_admin_email(self):
        """Test if send_admin_email works properly."""
        def verify_sent_email(request, mail):
            self.assertEqual(request.POST['subject'], mail.subject)
            self.assertEqual(request.POST['text'], mail.body)
            self.assertEqual(request.POST['sender'], mail.from_email)

        user = MockUser()
        default_sender = astakos_settings.SERVER_EMAIL

        # Test 1 - Check if malformed contact request raises BadRequest:
        #
        # a) Request with no POST dictionary.
        bad_request = {}

        with self.assertRaises(faults.BadRequest) as cm:
            utils.send_admin_email(user, bad_request)
        self.assertEqual("Contact request does not have a POST dictionary.",
                         cm.exception.message)

        # b) Request with required fields missing.
        bad_request = MockRequest({
            "subject": 'Subject',
            "sender": astakos_settings.SERVER_EMAIL,
        })

        with self.assertRaises(faults.BadRequest) as cm:
            utils.send_admin_email(user, bad_request)
        self.assertEqual(
            "Contact request does not have the following fields: text",
            cm.exception.message)

        # Test 2 - Check if email from default sender is sent properly and that
        # the default sender remains the same.
        request = MockRequest({
            "sender": astakos_settings.SERVER_EMAIL,
            "subject": 'Subject',
            "text": 'Body',
        })

        utils.send_admin_email(user, request)
        self.assertEqual(len(mail.outbox), 1)
        verify_sent_email(request, mail.outbox[0])
        self.assertEqual(default_sender, astakos_settings.SERVER_EMAIL)

        # Test 3 - Check if email from custom sender is sent properly and that
        # the default sender remains the same.
        request.update({"sender": 'admin@lemonparty.org'})

        utils.send_admin_email(user, request)
        self.assertEqual(len(mail.outbox), 2)
        verify_sent_email(request, mail.outbox[1])
        self.assertEqual(default_sender, astakos_settings.SERVER_EMAIL)

    def test_default_view(self):
        """Test if the default_view() function works as expected."""
        self.assertEqual(utils.default_view(), 'user')
        with override_settings(settings, ADMIN_VIEWS_ORDER=[]):
            reload_settings()
            self.assertEqual(utils.default_view(), None)

        with override_settings(settings, ADMIN_VIEWS_ORDER=['1', '2']):
            reload_settings()
            self.assertEqual(utils.default_view(), None)

        with override_settings(settings, ADMIN_VIEWS_ORDER=['1', 'user', '3']):
            reload_settings()
            self.assertEqual(utils.default_view(), 'user')

        reload_settings()

    def test_is_resource_useful(self):
        """Test if is_resource_useful function works as expected."""

        # Check if `is_resource_useful` produces the expected results,
        # regardless of the resource's unit.
        for unit in (None, "bytes"):
            r = MockResource(unit=unit)

            # Test if resource is useful, when its usage is zero
            self.assertTrue(utils.is_resource_useful(r, 2048))
            self.assertFalse(utils.is_resource_useful(r, 0))
            self.assertFalse(utils.is_resource_useful(r, PRACTICALLY_INFINITE))

            # Test if resource is useful, when its usage is not zero
            self.assertTrue(utils.is_resource_useful(r, 2048, 1024))
            self.assertTrue(utils.is_resource_useful(r, 0, 1024))
            self.assertFalse(utils.is_resource_useful(r, PRACTICALLY_INFINITE,
                                                      1024))


class TestAdminUtilsIntegration(AdminTestCase):

    """Integration test suite for admin utility functions."""

    def get_ip_or_404_helper(self, get_model_or_404):
        for ip_version in ['ipv4', 'ipv6']:
            model = getattr(self, ip_version, None)

            returned_model = get_model_or_404(model.id)
            self.assertEqual(model, returned_model)
            with self.assertRaises(AdminHttp404):
                get_model_or_404(gibberish(like='number'))

            returned_model = get_model_or_404(model.address)
            self.assertEqual(model, returned_model)
            with self.assertRaises(AdminHttp404):
                get_model_or_404(gibberish())

        self.ipv4_2 = mf.IPv4AddressFactory(address="1.2.3.4")
        self.ipv6_2 = mf.IPv6AddressFactory(address="::1")

        for ip_version in ['ipv4', 'ipv6']:
            model = getattr(self, ip_version, None)

            returned_model = get_model_or_404(model.id)
            self.assertEqual(model, returned_model)

            with self.assertRaises(AdminHttp404):
                returned_model = get_model_or_404(model.address)

    @for_all_views(model_views.keys())
    def test_get_or_404(self):
        mod = views.get_view_module_or_404(self.current_view)
        self.assertIsNotNone(mod)

        get_model_or_404 = getattr(mod, 'get_%s_or_404' % self.current_view,
                                   None)
        self.assertIsNotNone(get_model_or_404)

        # Special handling for ips
        if self.current_view == 'ip':
            self.get_ip_or_404_helper(get_model_or_404)
            return

        model = getattr(self, self.current_view, None)
        self.assertIsNotNone(model)

        if hasattr(model, 'uuid'):
            returned_model = get_model_or_404(model.uuid)
            self.assertEqual(model, returned_model)
            with self.assertRaises(AdminHttp404):
                get_model_or_404(gibberish())

        if hasattr(model, 'email'):
            returned_model = get_model_or_404(model.email)
            self.assertEqual(model, returned_model)
            with self.assertRaises(AdminHttp404):
                get_model_or_404(gibberish(like='email'))

        if hasattr(model, 'id'):
            returned_model = get_model_or_404(model.id)
            self.assertEqual(model, returned_model)
            with self.assertRaises(AdminHttp404):
                get_model_or_404(gibberish(like='number'))

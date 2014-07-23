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

import logging

from synnefo.db import models_factory as mf

from synnefo_admin import admin_settings
from synnefo_admin.admin import views
from synnefo_admin.admin.exceptions import AdminHttp404
from .common import for_all_views, AdminTestCase, gibberish

model_views = admin_settings.ADMIN_VIEWS.copy()
# Remove the model views that do not have details
model_views.pop('ip_log', None)
model_views.pop('group', None)


class TestAdminUtils(AdminTestCase):

    """Test suite for admin utility functions."""

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

        #logging.critical("View: %s", self.current_view)
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

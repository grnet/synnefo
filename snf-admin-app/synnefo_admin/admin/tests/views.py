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

#import logging
import mock
import functools
import unittest

import django.test
from django.conf import settings
from django.http import Http404
from django.core.urlresolvers import reverse

from synnefo_admin.admin import views
from synnefo_admin import admin_settings


USER1 = "5edcb5aa-1111-4146-a8ed-2b6287824353"
USER2 = "5edcb5aa-2222-4146-a8ed-2b6287824353"

USERS_UUIDS = {}
USERS_UUIDS[USER1] = {'displayname': 'testuser@test.com'}
USERS_UUIDS[USER2] = {'displayname': 'testuser2@test.com'}

USERS_DISPLAYNAMES = dict(map(lambda k: (k[1]['displayname'], {'uuid': k[0]}),
                          USERS_UUIDS.iteritems()))


def for_all_views(views=admin_settings.ADMIN_VIEWS.keys()):
    """Decorator that runs a test for all the specified views."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            for view in views:
                self.current_view = view
                func(self, *args, **kwargs)
        return wrapper
    return decorator


class AstakosClientMock():

    """Mock class for astakosclient."""

    def __init__(*args, **kwargs):
        pass

    def get_username(self, uuid):
        try:
            return USERS_UUIDS.get(uuid)['displayname']
        except TypeError:
            return None

    def get_uuid(self, display_name):
        try:
            return USERS_DISPLAYNAMES.get(display_name)['uuid']
        except TypeError:
            return None


class AuthClient(django.test.Client):

    """Mock class for Django AuthClient."""

    def request(self, **request):
        """Fill the HTTP_X_AUTH_TOKEN parameter with user token."""
        token = request.pop('user_token', '0000')
        if token:
            request['HTTP_X_AUTH_TOKEN'] = token
        return super(AuthClient, self).request(**request)


def get_user_mock(request, *args, **kwargs):
    """Mock function that fills an HTTP request.

    Return a different request based on the provided token. The '0000' token
    will return a request for an unauthorized user, while the '0001' token will
    return a request for an admin user.
    """
    request.user_uniq = None
    request.user = None
    if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0000':
        request.user_uniq = 'test'
        request.user = {"access": {
                        "token": {
                            "expires": "2013-06-19T15:23:59.975572+00:00",
                            "id": "0000",
                            "tenant": {
                                "id": "test",
                                "name": "Firstname Lastname"
                                }
                            },
                        "serviceCatalog": [],
                        "user": {
                            "roles_links": [],
                            "id": "test",
                            "roles": [{"id": 1, "name": "default"}],
                            "name": "Firstname Lastname"}}
                        }

    if request.META.get('HTTP_X_AUTH_TOKEN', None) == '0001':
        request.user_uniq = 'test'
        request.user = {"access": {
                        "token": {
                            "expires": "2013-06-19T15:23:59.975572+00:00",
                            "id": "0001",
                            "tenant": {
                                "id": "test",
                                "name": "Firstname Lastname"
                                }
                            },
                        "serviceCatalog": [],
                        "user": {
                            "roles_links": [],
                            "id": "test",
                            "roles": [{"id": 1, "name": "default"},
                                      {"id": 2, "name": "admin"}],
                            "name": "Firstname Lastname"}}
                        }


class TestAdminViewsUnit(unittest.TestCase):

    """Unit tests for admin views."""

    @for_all_views()
    def test_import_module_success(self):
        """Test if model view modules are imported successfully."""
        mod = views.get_view_module_or_404(self.current_view)
        self.assertIsNotNone(mod)

        view = views.get_json_view_or_404(self.current_view)
        self.assertIsNotNone(view)

    def test_import_module_fail(self):
        """Test if importing malformed view modules fails properly."""
        with self.assertRaises(Http404):
            views.get_view_module_or_404('asdgasdgasdg')
        with self.assertRaises(Http404):
            views.get_json_view_or_404('sdgasdgsdagsadg')


@mock.patch("astakosclient.AstakosClient", new=AstakosClientMock)
@mock.patch("snf_django.lib.astakos.get_user", new=get_user_mock)
class TestAdminViewsIntegration(django.test.TestCase):

    """Integration tests for admin views."""

    def setUp(self):
        """Common setUp method for all tests of this suite."""
        settings.SKIP_SSH_VALIDATION = True
        admin_settings.ADMIN_ENABLED = True
        self.client = AuthClient()

    def assertHttpStatusModelView(self, view, status, *args, **kwargs):
        """Hit all urls of model views and assert their status.

        For each view_type ('user', 'vm', ...) match three urls:
        1) admin-list, 2) admin-json, 3) admin-details.

        Hit each of these urls for the given view type and assert that the
        returned status is the same as the provided one.
        """
        # admin is disabled
        r = self.client.get(reverse('admin-list', args=[view]), *args,
                            **kwargs)
        self.assertEqual(r.status_code, status)

        r = self.client.get(reverse('admin-json', args=[view]), *args,
                            **kwargs)
        self.assertEqual(r.status_code, status)

        r = self.client.get(reverse('admin-details', args=[view, 'dummy']),
                            *args, **kwargs)
        self.assertEqual(r.status_code, status)

    @for_all_views()
    def test_enabled_setting_for_model_views(self):
        """Test if the ADMIN_ENABLED setting is respected by model views."""
        admin_settings.ADMIN_ENABLED = False
        self.assertHttpStatusModelView(self.current_view, 404,
                                       user_token="0001")

    @for_all_views(views=['stats-component', 'stats-component-details'])
    def test_enabled_setting_for_stats(self):
        """Test if the ADMIN_ENABLED setting is respected by stats views."""
        admin_settings.ADMIN_ENABLED = False

        # admin is disabled
        r = self.client.get(reverse('admin-%s' % self.current_view,
                                    args=['dummy']),
                            user_token="0001")
        self.assertEqual(r.status_code, 404)

    @for_all_views(views=['home', 'logout', 'charts', 'actions'])
    def test_enabled_setting_for_other_views(self):
        """Test if the ADMIN_ENABLED setting is respected by the rest views."""
        admin_settings.ADMIN_ENABLED = False

        # admin is disabled
        r = self.client.get(reverse('admin-%s' % self.current_view),
                            user_token="0001")
        self.assertEqual(r.status_code, 404)

    @for_all_views()
    def test_view_permissions_for_model_views(self):
        """Test if unauthorized users can access the admin views."""
        # anonymous user gets 403
        self.assertHttpStatusModelView(self.current_view, 403, user_token=None)

        # user not in admin group gets 403
        self.assertHttpStatusModelView(self.current_view, 403)

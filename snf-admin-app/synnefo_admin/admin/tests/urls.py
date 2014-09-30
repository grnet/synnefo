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

import sys

import django.test
from django.conf import settings
from django.core.urlresolvers import resolve, set_urlconf, Resolver404

from snf_django.utils.testing import override_settings

URL1 = "https://example.synnefo.org/rand0m"
URL2 = "https://admin.example.synnefo.org"


def reload_urlconf(urlconf=None):
    """Reload Synnefo's URLconf after ADMIN_BASE_URL is changed.

    This function should be called everytime ADMIN_BASE_URL is altered. It
    tries to propagate this change to the RegexURLResolver Django class by:
    a) Reloading the Admin settings and recalculating the BASE_PATH setting.
    b) Reloading the Admin urls, and thus recreating the Admin URLpatterns,
       which depend on the BASE_PATH setting.
    c) Reloading the Synnefo webproject URLs in order to integrate the new
       Admin URLs with the URLs of Synnefo.

    The cached Django RegexURLResolver has a pointer to the
    'synnefo.webproject.urls' module, so the changes should be instantly
    visible.

    The caller can optionally set a new URLconf to use.

    Before the end of the test, this function should always be called with no
    arguments once the ADMIN_BASE_URL is restored, in order to bring the test
    suite in its initial state.
    """
    reload(sys.modules['synnefo_admin.admin_settings'])
    reload(sys.modules['synnefo_admin.urls'])
    reload(sys.modules['synnefo.webproject.urls'])
    # Using this function with no urlconf will reset the ROOT_URLCONF to its
    # initial value.
    set_urlconf(urlconf)


class TestAdminUrls(django.test.TestCase):

    """Unit tests for Admin urls."""

    def tearDown(self):
        """Bring the URLpatterns to their initial state."""
        reload_urlconf()

    def test_url_resolving(self):
        """Test if URL resolving works properly.

        Check if the ADMIN_BASE_URL setting is used by Admin and if we have any
        issues with slashes and redirections.
        """
        ##
        # Test 1 - Default Admin URL.
        #
        # By default, the BASE_PATH for Admin is '/admin/'.
        r = resolve('/admin/')
        self.assertEqual(r.url_name, 'admin-default')

        # If we try to resolve the BASE_PATH without the slash, then we should
        # get redirected to the correct ('/admin/') URL.
        r = resolve('/admin')
        self.assertEqual(r.url_name, 'django.views.generic.simple.redirect_to')
        self.assertEqual(r.args, ())
        self.assertEqual(r.kwargs, {'url': 'admin/'})

        # Any URL that starts with the '/admin' string but has extra characters
        # should return 404.
        with self.assertRaises(Resolver404):
            r = resolve('/adminandoopstoomanychars')

        ##
        # Test 2 - Custom Admin URL with suffix. This tests if URL resolving
        # works properly when using a custom ADMIN_BASE_URL with a unique
        # suffix.

        # Change the ADMIN_BASE_URL and update the URLpatterns of Synnefo.
        with override_settings(settings, ADMIN_BASE_URL=URL1):
            reload_urlconf()

            # Check that the '/admin/' URL no longer works.
            with self.assertRaises(Resolver404):
                r = resolve('/admin/')

            # The new BASE_PATH should be 'rand0m'. Check if the resolved view
            # is the expected.
            r = resolve('/rand0m/')
            self.assertEqual(r.url_name, 'admin-default')

            # Check if resolving the BASE_PATH without a slash redirects us
            # properly.
            r = resolve('/rand0m')
            self.assertEqual(r.url_name,
                             'django.views.generic.simple.redirect_to')
            self.assertEqual(r.args, ())
            self.assertEqual(r.kwargs, {'url': 'rand0m/'})

            # Check if extra characters return 404.
            with self.assertRaises(Resolver404):
                r = resolve('/rand0mandoopstoomanychars')

        ##
        # Test 3 - Custom Admin URL without suffix. This tests if URL resolving
        # works properly when using a custom ADMIN_BASE_URL that points to a
        # node only, with no extra suffix.

        # Although Admin can be installed in a separate node from the
        # Cyclades/Astakos nodes, their packages - and by extension their
        # URLPatterns - will be installed in the Admin node. In order to "hide"
        # their urls, we will use the Admin urls as our ROOT_URLCONF for this
        # part of the test.
        with override_settings(settings, ADMIN_BASE_URL=URL2):
            reload_urlconf('synnefo_admin.urls')

            # Check that hitting the node URL sends us to Admin.
            r = resolve('/')
            self.assertEqual(r.url_name, 'admin-default')

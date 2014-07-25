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

import functools
import django.test
import string
import random
import mock

from astakos.im.tests.projects import ProjectAPITest
from astakos.im.functions import approve_application
from synnefo.db import models_factory as mf

from synnefo_admin import admin_settings


USER1 = "5edcb5aa-1111-4146-a8ed-2b6287824353"
USER2 = "5edcb5aa-2222-4146-a8ed-2b6287824353"

USERS_UUIDS = {}
USERS_UUIDS[USER1] = {'displayname': 'testuser@test.com'}
USERS_UUIDS[USER2] = {'displayname': 'testuser2@test.com'}

USERS_DISPLAYNAMES = dict(map(lambda k: (k[1]['displayname'], {'uuid': k[0]}),
                          USERS_UUIDS.iteritems()))


def gibberish(length=10, like='string'):
    """Create a random number, a gibberish string or email."""
    if like not in ['string', 'number', 'email']:
        raise Exception("You gave me gibberish: %s" % (like))

    matrix = string.digits
    if not like == 'number':
        matrix += string.ascii_letters

    if like == 'email':
        if length < 8:
            raise Exception("Can't create email with less than 8 characters")
        # Remove '@', '.' and TLD (always 2 chars)
        length -= 4
        tld = gibberish(2)
        dom_len = length / 2
        domain = gibberish(dom_len)
        name_len = length - dom_len
        name = gibberish(name_len)
        return name + '@' + domain + '.' + tld

    gib_list = [random.choice(matrix) for n in xrange(length)]
    gib = ''.join(gib_list)

    return gib if not like == 'number' else int(gib)


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


@mock.patch("astakosclient.AstakosClient", new=AstakosClientMock)
@mock.patch("snf_django.lib.astakos.get_user", new=get_user_mock)
class AdminTestCase(ProjectAPITest):

    """Generic TestCase for admin tests.

    This TestCase class is based on the ProjectAPITest class, which has some
    useful functions and Astakos models already created. We enhance the above
    by adding model instances through the model_factory of cyclades.
    """

    def setUp(self):
        """Common setUp for all AdminTestCases.

        This setUp method will create and approve a project as well as add
        several Cyclades model instances using Cyclades' model_factory.
        """
        ProjectAPITest.setUp(self)
        # Create a simple project.
        h_owner = {"HTTP_X_AUTH_TOKEN": self.user1.auth_token}

        app1 = {"name": "test.pr",
                "description": u"δεσκρίπτιον",
                "end_date": "2013-5-5T20:20:20Z",
                "join_policy": "auto",
                "max_members": 5,
                "resources": {u"σέρβις1.ρίσορς11": {
                    "project_capacity": 1024,
                    "member_capacity": 512}}
                }
        status, body = self.create(app1, h_owner)

        # Ensure that the project application has been created.
        self.assertEqual(status, 201)
        project_id = body["id"]
        app_id = body["application"]

        # Approve the application.
        self.project = approve_application(app_id, project_id)
        self.assertIsNotNone(self.project)

        # Alias owner user with a generic name
        self.user = self.user1

        # Create cyclades models.
        self.vm = mf.VirtualMachineFactory()
        self.volume = mf.VolumeFactory()
        self.network = mf.NetworkFactory()
        self.ipv4 = mf.IPv4AddressFactory(address="1.2.3.4")
        self.ipv6 = mf.IPv6AddressFactory(address="::1")

    # Override the test_projects function of ProjectAPITest class so that it
    # doesn't get called.
    test_projects = None

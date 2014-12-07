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
from django.contrib.auth.backends import ModelBackend

from astakos.im.models import AstakosUser
from astakos.im import settings
from astakos.im import auth_providers as auth

try:
    from django_auth_ldap.backend import\
        LDAPBackend as LDAPAuthenticationBackend
except ImportError as e:
    if 'ldap' in settings.IM_MODULES:
        msg = ("%s. 'django_auth_ldap' package is required when LDAP"
               " authentication provider is used." % str(e))
        raise ImportError(msg)
    else:
        LDAPAuthenticationBackend = object


logger = logging.getLogger(__name__)


class TokenBackend(ModelBackend):
    """
    AuthenticationBackend used to authenticate using token instead
    """
    def authenticate(self, email=None, auth_token=None):
        try:
            user = AstakosUser.objects.get_by_identifier(email, is_active=True,
                                                         auth_token=auth_token)
            return user
        except AstakosUser.DoesNotExist:
            return None
        else:
            msg = 'Invalid token during authentication for %s'
            logger.log(settings.LOGGING_LEVEL, msg, email)

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None


class EmailBackend(ModelBackend):
    """
    If the ``username`` parameter is actually an email uses email to
    authenticate the user else tries the username.

    Used from ``astakos.im.forms.LoginForm`` to authenticate.
    """
    def authenticate(self, username=None, password=None):
        # First check whether a user having this email exists
        try:
            user = AstakosUser.objects.get_by_identifier(username)
        except AstakosUser.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        else:
            msg = 'Invalid password during authentication for %s'
            logger.log(settings.LOGGING_LEVEL, msg, username)

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None


LDAP_PROVIDER = auth.get_provider('ldap')


class MockedAstakosUser(object):
    """Mock AstakosUser object to be used by LDAPBackend.

    The 'LDAPAuthenticationBackend' requires the creation or existence of an
    Django User object. However, the creation of the 'AstakosUser' by the
    'LDAPAuthenticationBackend' does not match with how Astakos is handling
    thirt party authentication providers. To overcome this issue we create
    a mock object, whose attributes will be populated by the
    'LDAPAuthenticationBackend'.

    """
    def set_unusable_password(self):
        pass

    def get_profile(self):
        return None

    def save(self, *args, **kwargs):
        pass


class LDAPBackend(LDAPAuthenticationBackend):
    """Authentication Backend for LDAP provider.

    Override 'get_or_create_user' method of 'django_auth_ldap.LDAPBackend' to
    create a mocked User object instead of automatically creating the User in
    DB. This is required in order to go with how Astakos is handling third
    party providers.

    """
    def get_or_create_user(self, username, ldap_user):
        user = MockedAstakosUser()
        user.username = username
        return user, True

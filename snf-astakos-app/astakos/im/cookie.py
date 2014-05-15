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

from urllib import quote, unquote

from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext as _

from astakos.im import settings
import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


class CookieHandler():
    def __init__(self, request, response=None):
        cookies = getattr(request, 'COOKIES', {})
        cookie = unquote(cookies.get(settings.COOKIE_NAME, ''))
        self.uuid, sep, self.auth_token = cookie.partition('|')
        self.request = request
        self.response = response

    @property
    def uuid(self):
        return getattr(self, 'uuid', '')

    @property
    def auth_token(self):
        return getattr(self, 'auth_token', '')

    @property
    def is_set(self):
        no_token = not self.auth_token
        return not no_token

    @property
    def is_valid(self):
        cookie_attribute = ('uuid' if not settings.TRANSLATE_UUIDS
                            else 'username')
        return (self.uuid == getattr(self.user, cookie_attribute, '') and
                self.auth_token == getattr(self.user, 'auth_token', ''))

    @property
    def user(self):
        return getattr(self.request, 'user', AnonymousUser())

    def __set(self):
        if not self.response:
            raise ValueError(_(astakos_messages.NO_RESPONSE))
        user = self.user
        expire_fmt = user.auth_token_expires.strftime(
            '%a, %d-%b-%Y %H:%M:%S %Z')
        if settings.TRANSLATE_UUIDS:
            cookie_value = quote(user.username + '|' + user.auth_token)
        else:
            cookie_value = quote(user.uuid + '|' + user.auth_token)
        self.response.set_cookie(
            settings.COOKIE_NAME, value=cookie_value, expires=expire_fmt,
            path='/', domain=settings.COOKIE_DOMAIN,
            secure=settings.COOKIE_SECURE)
        msg = 'Cookie [expiring %s] set for %s'
        logger.log(settings.LOGGING_LEVEL, msg, user.auth_token_expires,
                   user.uuid)

    def __delete(self):
        if not self.response:
            raise ValueError(_(astakos_messages.NO_RESPONSE))
        self.response.delete_cookie(
            settings.COOKIE_NAME, path='/', domain=settings.COOKIE_DOMAIN)
        msg = 'Cookie deleted for %s'
        logger.log(settings.LOGGING_LEVEL, msg, self.uuid)

    def fix(self, response=None):
        self.response = response or self.response
        try:
            if self.user.is_authenticated():
                if not self.is_set or not self.is_valid:
                    self.__set()
            else:
                if self.is_set:
                    self.__delete()
        except AttributeError:
            pass

# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import logging

from urllib import quote, unquote

from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext as _

from astakos.im.settings import (
    COOKIE_NAME, COOKIE_DOMAIN, COOKIE_SECURE, LOGGING_LEVEL, TRANSLATE_UUIDS)

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


class Cookie():
    def __init__(self, request, response=None):
        cookies = getattr(request, 'COOKIES', {})
        cookie = unquote(cookies.get(COOKIE_NAME, ''))
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
        cookie_attribute = 'uuid' if not TRANSLATE_UUIDS else 'username'
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
        if TRANSLATE_UUIDS:
            cookie_value = quote(user.username + '|' + user.auth_token)
        else:
            cookie_value = quote(user.uuid + '|' + user.auth_token)
        self.response.set_cookie(
            COOKIE_NAME, value=cookie_value, expires=expire_fmt, path='/',
            domain=COOKIE_DOMAIN, secure=COOKIE_SECURE
        )
        msg = 'Cookie [expiring %(auth_token_expires)s] set for %(uuid)s' % user.__dict__
        logger._log(LOGGING_LEVEL, msg, [])

    def __delete(self):
        if not self.response:
            raise ValueError(_(astakos_messages.NO_RESPONSE))
        self.response.delete_cookie(COOKIE_NAME, path='/', domain=COOKIE_DOMAIN)
        msg = 'Cookie deleted for %(uuid)s' % self.__dict__
        logger._log(LOGGING_LEVEL, msg, [])

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

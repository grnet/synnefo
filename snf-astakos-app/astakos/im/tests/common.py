# Copyright 2011 GRNET S.A. All rights reserved.
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

from contextlib import contextmanager

import copy
import datetime
import functools

from snf_django.utils.testing import with_settings, override_settings, assertIn

from django.test import Client
from django.test import TransactionTestCase as TestCase
from django.core import mail
from django.http import SimpleCookie, HttpRequest, QueryDict
from django.utils.importlib import import_module
from django.utils import simplejson as json

from astakos.im.activation_backends import *
from astakos.im.views.target.shibboleth import Tokens as ShibbolethTokens
from astakos.im.models import *
from astakos.im import functions
from astakos.im import settings as astakos_settings
from astakos.im import forms
from astakos.im import activation_backends

from urllib import quote
from datetime import timedelta

from astakos.im import messages
from astakos.im import auth_providers
from astakos.im import quotas
from astakos.im import resources

from django.conf import settings


# set some common settings
astakos_settings.EMAILCHANGE_ENABLED = True
astakos_settings.RECAPTCHA_ENABLED = False

settings.LOGGING_SETUP['disable_existing_loggers'] = False

# shortcut decorators to override provider settings
# e.g. shibboleth_settings(ENABLED=True) will set
# ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_ENABLED = True in global synnefo settings
prefixes = {'providers': 'AUTH_PROVIDER_',
            'shibboleth': 'ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_',
            'local': 'ASTAKOS_AUTH_PROVIDER_LOCAL_'}
im_settings = functools.partial(with_settings, astakos_settings)
shibboleth_settings = functools.partial(with_settings,
                                        settings,
                                        prefix=prefixes['shibboleth'])
localauth_settings = functools.partial(with_settings, settings,
                                       prefix=prefixes['local'])


class AstakosTestClient(Client):
    pass


class ShibbolethClient(AstakosTestClient):
    """
    A shibboleth agnostic client.
    """
    VALID_TOKENS = filter(lambda x: not x.startswith("_"),
                          dir(ShibbolethTokens))

    def __init__(self, *args, **kwargs):
        self.tokens = kwargs.pop('tokens', {})
        super(ShibbolethClient, self).__init__(*args, **kwargs)

    def set_tokens(self, **kwargs):
        for key, value in kwargs.iteritems():
            key = 'SHIB_%s' % key.upper()
            if not key in self.VALID_TOKENS:
                raise Exception('Invalid shibboleth token')

            self.tokens[key] = value

    def unset_tokens(self, *keys):
        for key in keys:
            key = 'SHIB_%s' % param.upper()
            if key in self.tokens:
                del self.tokens[key]

    def reset_tokens(self):
        self.tokens = {}

    def get_http_token(self, key):
        http_header = getattr(ShibbolethTokens, key)
        return http_header

    def request(self, **request):
        """
        Transform valid shibboleth tokens to http headers
        """
        for token, value in self.tokens.iteritems():
            request[self.get_http_token(token)] = value

        for param in request.keys():
            key = 'SHIB_%s' % param.upper()
            if key in self.VALID_TOKENS:
                request[self.get_http_token(key)] = request[param]
                del request[param]

        return super(ShibbolethClient, self).request(**request)


def get_user_client(username, password="password"):
    client = Client()
    client.login(username=username, password=password)
    return client


def get_local_user(username, **kwargs):
        try:
            return AstakosUser.objects.get(email=username)
        except:
            user_params = {
                'username': username,
                'email': username,
                'is_active': True,
                'activation_sent': datetime.now(),
                'email_verified': True
            }
            user_params.update(kwargs)
            user = AstakosUser(**user_params)
            user.set_password(kwargs.get('password', 'password'))
            user.renew_verification_code()
            user.save()
            user.add_auth_provider('local', auth_backend='astakos')
            if kwargs.get('is_active', True):
                user.is_active = True
            else:
                user.is_active = False
            user.save()
            return user


def get_mailbox(email):
    mails = []
    for sent_email in mail.outbox:
        for recipient in sent_email.recipients():
            if email in recipient:
                mails.append(sent_email)
    return mails

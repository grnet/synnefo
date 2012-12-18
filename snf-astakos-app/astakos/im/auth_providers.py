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


from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.datastructures import SortedDict

from django.conf import settings

from astakos.im import settings as astakos_settings
from astakos.im import messages as astakos_messages

import logging

logger = logging.getLogger(__name__)

# providers registry
PROVIDERS = {}

class AuthProviderBase(type):

    def __new__(cls, name, bases, dct):
        include = False
        if [b for b in bases if isinstance(b, AuthProviderBase)]:
            type_id = dct.get('module')
            if type_id:
                include = True
            if type_id in astakos_settings.IM_MODULES:
                dct['module_enabled'] = True

        newcls = super(AuthProviderBase, cls).__new__(cls, name, bases, dct)
        if include:
            PROVIDERS[type_id] = newcls
        return newcls


class AuthProvider(object):

    __metaclass__ = AuthProviderBase

    module = None
    module_active = False
    module_enabled = False
    one_per_user = False
    login_prompt = _('Login using ')
    primary_login_prompt = _('Login using ')

    def get_message(self, msg, **kwargs):
        params = kwargs
        params.update({'provider': self.get_title_display})

        override_msg = getattr(self, 'get_%s_message_display' % msg.lower(), None)
        msg = 'AUTH_PROVIDER_%s' % msg
        return override_msg or getattr(astakos_messages, msg, msg) % params

    def __init__(self, user=None):
        self.user = user

    def __getattr__(self, key):
        if not key.startswith('get_'):
            return super(AuthProvider, self).__getattribute__(key)

        if key.endswith('_display') or key.endswith('template'):
            attr = key.replace('_display', '').replace('get_','')
            settings_attr = self.get_setting(attr.upper())
            if not settings_attr:
                return getattr(self, attr)
            return _(settings_attr)
        else:
            return super(AuthProvider, self).__getattr__(key)

    def get_setting(self, name, default=None):
        attr = 'ASTAKOS_AUTH_PROVIDER_%s_%s' % (self.module.upper(), name.upper())
        attr_sec = 'ASTAKOS_%s_%s' % (self.module.upper(), name.upper())
        if not hasattr(settings, attr):
            return getattr(settings, attr_sec, default)
        return getattr(settings, attr, default)

    def is_available_for_login(self):
        """ A user can login using authentication provider"""
        return self.is_active() and self.get_setting('CAN_LOGIN',
                                                     self.is_active())

    def is_available_for_create(self):
        """ A user can create an account using this provider"""
        return self.is_active() and self.get_setting('CAN_CREATE',
                                                   self.is_active())

    def is_available_for_add(self):
        """ A user can assign provider authentication method"""
        return self.is_active() and self.get_setting('CAN_ADD',
                                                   self.is_active())

    def is_active(self):
        return self.module in astakos_settings.IM_MODULES


class LocalAuthProvider(AuthProvider):
    module = 'local'
    title = _('Local password')
    description = _('Create a local password for your account')
    add_prompt =  _('Create a local password for your account')
    login_prompt = _('if you already have a username and password')
    signup_prompt = _('New to ~okeanos ?')
    signup_link_prompt = _('create an account now')


    @property
    def add_url(self):
        return reverse('password_change')

    one_per_user = True

    login_template = 'im/auth/local_login_form.html'
    login_prompt_template = 'im/auth/local_login_prompt.html'
    signup_prompt_template = 'im/auth/local_signup_prompt.html'
    details_tpl = _('You can login to your account using your'
                    ' %(auth_backend)s password.')

    @property
    def extra_actions(self):
        return [(_('Change password'), reverse('password_change')), ]


class ShibbolethAuthProvider(AuthProvider):
    module = 'shibboleth'
    title = _('Academic credentials (Shibboleth)')
    add_prompt = _('Allows you to login to your account using your academic '
                    'account')
    details_tpl = _('Shibboleth account \'%(identifier)s\' is connected to your '
                    ' account.')
    user_title = _('Academic credentials (%(identifier)s)')
    primary_login_prompt = _('If you are a student/researcher/faculty you can'
                             ' login using your university-credentials in'
                             ' the following page')

    @property
    def add_url(self):
        return reverse('astakos.im.target.shibboleth.login')

    login_template = 'im/auth/shibboleth_login.html'
    login_prompt_template = 'im/auth/shibboleth_login_prompt.html'


class TwitterAuthProvider(AuthProvider):
    module = 'twitter'
    title = _('Twitter')
    add_prompt = _('Allows you to login to your account using Twitter')
    details_tpl = _('Twitter screen name: %(info_screen_name)s')
    user_title = _('Twitter (%(info_screen_name)s)')

    @property
    def add_url(self):
        return reverse('astakos.im.target.twitter.login')

    login_template = 'im/auth/third_party_provider_generic_login.html'
    login_prompt_template = 'im/auth/third_party_provider_generic_login_prompt.html'


class GoogleAuthProvider(AuthProvider):
    module = 'google'
    title = _('Google')
    add_prompt = _('Allows you to login to your account using Google')
    details_tpl = _('Google account: %(info_email)s')
    user_title = _('Google (%(info_email)s)')

    @property
    def add_url(self):
        return reverse('astakos.im.target.google.login')

    login_template = 'im/auth/third_party_provider_generic_login.html'
    login_prompt_template = 'im/auth/third_party_provider_generic_login_prompt.html'


class LinkedInAuthProvider(AuthProvider):
    module = 'linkedin'
    title = _('LinkedIn')
    add_prompt = _('Allows you to login to your account using LinkedIn')
    user_title = _('LinkedIn (%(info_emailAddress)s)')
    details_tpl = _('LinkedIn account: %(info_emailAddress)s')

    @property
    def add_url(self):
        return reverse('astakos.im.target.linkedin.login')

    login_template = 'im/auth/third_party_provider_generic_login.html'
    login_prompt_template = 'im/auth/third_party_provider_generic_login_prompt.html'


def get_provider(id, user_obj=None, default=None):
    """
    Return a provider instance from the auth providers registry.
    """
    return PROVIDERS.get(id, default)(user_obj)


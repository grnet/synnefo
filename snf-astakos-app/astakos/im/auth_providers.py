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

from astakos.im import settings

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
            if type_id in settings.IM_MODULES:
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

    def __init__(self, user=None):
        self.user = user

    def get_setting(self, name, default=None):
        attr = 'AUTH_PROVIDER_%s_%s' % (self.module.upper(), name.upper())
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
        return self.module in settings.IM_MODULES


class LocalAuthProvider(AuthProvider):
    module = 'local'
    title = _('Local password')
    description = _('Create a local password for your account')


    @property
    def add_url(self):
        return reverse('password_change')

    add_description = _('Create a local password for your account')
    login_template = 'auth/local_login_form.html'
    add_template = 'auth/local_add_action.html'
    one_per_user = True
    details_tpl = _('You can login to your account using your'
                    ' %(auth_backend)s password.')

    @property
    def extra_actions(self):
        return [(_('Change password'), reverse('password_change')), ]


class ShibbolethAuthProvider(AuthProvider):
    module = 'shibboleth'
    title = _('Academic credentials (Shibboleth)')
    description = _('Allows you to login to your account using your academic '
                    'credentials')

    @property
    def add_url(self):
        return reverse('astakos.im.target.shibboleth.login')

    add_description = _('Allows you to login to your account using your academic '
                    'credentials')
    login_template = 'auth/shibboleth_login_form.html'
    add_template = 'auth/shibboleth_add_action.html'
    details_tpl = _('You can login to your account using your'
                    ' shibboleth credentials. Shibboleth id: %(identifier)s')


def get_provider(id, user_obj=None, default=None):
    """
    Return a provider instance from the auth providers registry.
    """
    return PROVIDERS.get(id, default)(user_obj)


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

import copy
import json

from synnefo.lib.ordereddict import OrderedDict

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.contrib.auth.models import Group
from django import template

from django.conf import settings

from astakos.im import settings as astakos_settings
from astakos.im import messages as astakos_messages

from synnefo_branding import utils as branding_utils

import logging

logger = logging.getLogger(__name__)

# providers registry
PROVIDERS = {}
REQUIRED_PROVIDERS = {}


class AuthProviderBase(type):

    def __new__(cls, name, bases, dct):
        include = False
        if [b for b in bases if isinstance(b, AuthProviderBase)]:
            type_id = dct.get('module')
            if type_id:
                include = True
            if type_id in astakos_settings.IM_MODULES:
                if astakos_settings.IM_MODULES.index(type_id) == 0:
                    dct['is_primary'] = True
                dct['module_enabled'] = True

        newcls = super(AuthProviderBase, cls).__new__(cls, name, bases, dct)
        if include:
            PROVIDERS[type_id] = newcls
            if newcls().get_required_policy:
                REQUIRED_PROVIDERS[type_id] = newcls
        return newcls


class AuthProvider(object):

    __metaclass__ = AuthProviderBase

    module = None
    module_enabled = False
    is_primary = False

    message_tpls = OrderedDict((
        ('title', '{module_title}'),
        ('login_title', '{title} LOGIN'),
        ('method_prompt', '{title} login'),
        ('account_prompt', '{title} account'),
        ('signup_title', '{title}'),
        ('profile_title', '{title}'),
        ('method_details', '{account_prompt}: {identifier}'),
        ('primary_login_prompt', 'Login using '),
        ('required', '{title} is required. You can assign it '
                     'from your profile page'),
        ('login_prompt', ''),
        ('add_prompt', 'Allows you to login using {title}'),
        ('login_extra', ''),
        ('username', '{username}'),
        ('disabled_for_create', 'It seems this is the first time you\'re '
                                'trying to access {service_name}. '
                                'Unfortunately, we are not accepting new '
                                'users at this point.'),
        ('switch_success', 'Account changed successfully.'),
        ('cannot_login', '{title} is not available for login. '
                         'Please use one of your other available methods '
                         'to login ({available_methods_links}'),

        # icons should end with _icon
        ('module_medium_icon', 'im/auth/icons-medium/{module}.png'),
        ('module_icon', 'im/auth/icons/{module}.png'))
    )

    messages = {}
    module_urls = {}

    remote_authenticate = True
    remote_logout_url = None

    # templates
    primary_login_template = 'im/auth/generic_primary_login.html'
    login_template = 'im/auth/generic_login.html'
    signup_template = 'im/signup.html'
    login_prompt_template = 'im/auth/generic_login_prompt.html'
    signup_prompt_template = 'im/auth/signup_prompt.html'

    default_policies = {
        'login': True,
        'create': True,
        'add': True,
        'remove': True,
        'limit': 1,
        'switch': True,
        'add_groups': [],
        'creation_groups': [],
        'required': False,
        'automoderate': not astakos_settings.MODERATION_ENABLED
    }

    policies = {}

    def __init__(self, user=None, identifier=None, **provider_params):
        """
        3 ways to initialize (no args, user, user and identifier).

        no args: Used for anonymous unauthenticated users.
        >>> p = auth_providers.get_provider('local')
        >>> # check that global settings allows us to create a new account
        >>> # using `local` provider.
        >>> print p.is_available_for_create()

        user and identifier: Used to provide details about a user's specific
        login method.
        >>> p = auth_providers.get_provider('google', user,
        >>>                                 identifier='1421421')
        >>> # provider (google) details prompt
        >>> print p.get_method_details()
        "Google account: 1421421"
        """

        # handle AnonymousUser instance
        self.user = None
        if user and hasattr(user, 'pk') and user.pk:
            self.user = user

        self.identifier = identifier
        self._instance = None
        if 'instance' in provider_params:
            self._instance = provider_params['instance']
            del provider_params['instance']

        # initialize policies
        self.module_policies = copy.copy(self.default_policies)
        self.module_policies['automoderate'] = not \
            astakos_settings.MODERATION_ENABLED
        for policy, value in self.policies.iteritems():
            setting_key = "%s_POLICY" % policy.upper()
            if self.has_setting(setting_key):
                self.module_policies[policy] = self.get_setting(setting_key)
            else:
                self.module_policies[policy] = value

        # messages cache
        self.message_tpls_compiled = OrderedDict()

        # module specific messages
        self.message_tpls = OrderedDict(self.message_tpls)
        for key, value in self.messages.iteritems():
            self.message_tpls[key] = value

        self._provider_details = provider_params

        self.resolve_available_methods = True

    def get_provider_model(self):
        from astakos.im.models import AstakosUserAuthProvider as AuthProvider
        return AuthProvider

    def remove_from_user(self):
        if not self.get_remove_policy:
            raise Exception("Provider cannot be removed")

        for group_name in self.get_add_groups_policy:
            group = Group.objects.get(name=group_name)
            self.user.groups.remove(group)
            self.log('removed from group due to add_groups_policy %s',
                     group.name)

        self._instance.delete()
        self.log('removed')

    def add_to_user(self, **params):
        if self._instance:
            raise Exception("Cannot add an existing provider")

        create = False
        if self.get_user_providers().count() == 0:
            create = True

        if create and not self.get_create_policy:
            raise Exception("Provider not available for create")

        if not self.get_add_policy:
            raise Exception("Provider cannot be added")

        if create:
            for group_name in self.get_creation_groups_policy:
                group, created = Group.objects.get_or_create(name=group_name)
                self.user.groups.add(group)
                self.log("added to %s group due to creation_groups_policy",
                         group_name)

        for group_name in self.get_add_groups_policy:
            group, created = Group.objects.get_or_create(name=group_name)
            self.user.groups.add(group)
            self.log("added to %s group due to add_groups_policy",
                     group_name)

        if self.identifier:
            pending = self.get_provider_model().objects.unverified(
                self.module, identifier=self.identifier)

            if pending:
                pending._instance.delete()

        create_params = {
            'module': self.module,
            'info_data': json.dumps(self.provider_details.get('info', {})),
            'active': True,
            'identifier': self.identifier
        }
        if 'info' in self.provider_details:
            del self.provider_details['info']

        create_params.update(self.provider_details)
        create_params.update(params)
        create = self.user.auth_providers.create(**create_params)
        self.log("created %r" % create_params)
        return create

    def __repr__(self):
        r = "'%s' module" % self.__class__.__name__
        if self.user:
            r += ' (user: %s)' % self.user
        if self.identifier:
            r += '(identifier: %s)' % self.identifier
        return r

    def _message_params(self, **extra_params):
        """
        Retrieve message formating parameters.
        """
        params = {'module': self.module, 'module_title': self.module.title()}
        if self.identifier:
            params['identifier'] = self.identifier

        if self.user:
            for key, val in self.user.__dict__.iteritems():
                params["user_%s" % key.lower()] = val

        if self.provider_details:
            for key, val in self.provider_details.iteritems():
                params["provider_%s" % key.lower()] = val

            if 'info' in self.provider_details:
                if isinstance(self.provider_details['info'], basestring):
                    self.provider_details['info'] = \
                        json.loads(self.provider_details['info'])
                for key, val in self.provider_details['info'].iteritems():
                    params['provider_info_%s' % key.lower()] = val

        # resolve username, handle unexisting defined username key
        if self.user and self.username_key in params:
            params['username'] = params[self.username_key]
        else:
            params['username'] = self.identifier

        branding_params = dict(map(lambda k: (k[0].lower(), k[1]),
            branding_utils.get_branding_dict().iteritems()))
        params.update(branding_params)

        if not self.message_tpls_compiled:
            for key, message_tpl in self.message_tpls.iteritems():
                msg = self.messages.get(key, self.message_tpls.get(key))
                override_in_settings = self.get_setting(key)
                if override_in_settings is not None:
                    msg = override_in_settings
                try:
                    self.message_tpls_compiled[key] = msg.format(**params)
                    params.update(self.message_tpls_compiled)
                except KeyError, e:
                    continue
        else:
            params.update(self.message_tpls_compiled)

        for key, value in self.urls.iteritems():
            params['%s_url' % key] = value

        if self.user and self.resolve_available_methods:
            available_providers = self.user.get_enabled_auth_providers()
            for p in available_providers:
                p.resolve_available_methods = False
                if p.module == self.module and p.identifier == self.identifier:
                    available_providers.remove(p)

            get_msg = lambda p: p.get_method_prompt_msg
            params['available_methods'] = \
                ','.join(map(get_msg, available_providers))

            get_msg = lambda p: "<a href='%s'>%s</a>" % \
                (p.get_login_url, p.get_method_prompt_msg)

            params['available_methods_links'] = \
                ','.join(map(get_msg, available_providers))

        params.update(extra_params)
        return params

    def get_template(self, tpl):
        tpls = ['im/auth/%s_%s.html' % (self.module, tpl),
                getattr(self, '%s_template' % tpl)]
        found = None
        for tpl in tpls:
            try:
                found = template.loader.get_template(tpl)
                return tpl
            except template.TemplateDoesNotExist:
                continue
        if not found:
            raise template.TemplateDoesNotExist
        return tpl

    def get_username(self):
        return self.get_username_msg

    def get_user_providers(self):
        return self.user.auth_providers.active().filter(
            module__in=astakos_settings.IM_MODULES)

    def get_user_module_providers(self):
        return self.user.auth_providers.active().filter(module=self.module)

    def get_existing_providers(self):
        return ""

    def verified_exists(self):
        return self.get_provider_model().objects.verified(
            self.module, identifier=self.identifier)

    def resolve_policy(self, policy, default=None):

        if policy == 'switch' and default and not self.get_add_policy:
            return not self.get_policy('remove')

        if not self.user:
            return default

        if policy == 'remove' and default is True:
            return self.get_user_providers().count() > 1

        if policy == 'add' and default is True:
            limit = self.get_policy('limit')
            if limit <= self.get_user_module_providers().count():
                return False

            if self.identifier:
                if self.verified_exists():
                    return False

        return default

    def get_user_policies(self):
        from astakos.im.models import AuthProviderPolicyProfile
        return AuthProviderPolicyProfile.objects.for_user(self.user,
                                                          self.module)

    def get_policy(self, policy):
        module_default = self.module_policies.get(policy)
        settings_key = '%s_POLICY' % policy.upper()
        settings_default = self.get_setting(settings_key, module_default)

        if self.user:
            user_policies = self.get_user_policies()
            settings_default = user_policies.get(policy, settings_default)

        return self.resolve_policy(policy, settings_default)

    def get_message(self, msg, **extra_params):
        """
        Retrieve an auth provider message
        """
        if msg.endswith('_msg'):
            msg = msg.replace('_msg', '')
        params = self._message_params(**extra_params)

        # is message ???
        tpl = self.message_tpls_compiled.get(msg.lower(), None)
        if not tpl:
            msg_key = 'AUTH_PROVIDER_%s' % msg.upper()
            try:
                tpl = getattr(astakos_messages, msg_key)
            except AttributeError, e:
                try:
                    msg_key = msg.upper()
                    tpl = getattr(astakos_messages, msg_key)
                except AttributeError, e:
                    tpl = ''

        in_settings = self.get_setting(msg)
        if in_settings:
            tpl = in_settings

        return tpl.format(**params)

    @property
    def urls(self):
        urls = {
            'login': reverse(self.login_view),
            'add': reverse(self.login_view),
            'profile': reverse('edit_profile'),
        }
        if self.user:
            urls.update({
                'resend_activation': self.user.get_resend_activation_url(),
            })
        if self.identifier and self._instance:
            urls.update({
                'switch': reverse(self.login_view) + '?switch_from=%d' %
                self._instance.pk,
                'remove': reverse('remove_auth_provider',
                                  kwargs={'pk': self._instance.pk})
            })
        urls.update(self.module_urls)
        return urls

    def get_setting_key(self, name):
        return 'ASTAKOS_AUTH_PROVIDER_%s_%s' % (self.module.upper(),
                                                name.upper())

    def get_global_setting_key(self, name):
        return 'ASTAKOS_AUTH_PROVIDERS_%s' % name.upper()

    def has_global_setting(self, name):
        return hasattr(settings, self.get_global_setting_key(name))

    def has_setting(self, name):
        return hasattr(settings, self.get_setting_key(name))

    def get_setting(self, name, default=None):
        attr = self.get_setting_key(name)
        if not self.has_setting(name):
            return self.get_global_setting(name, default)
        return getattr(settings, attr, default)

    def get_global_setting(self, name, default=None):
        attr = self.get_global_setting_key(name)
        if not self.has_global_setting(name):
            return default
        return getattr(settings, attr, default)

    @property
    def provider_details(self):
        if self._provider_details:
            return self._provider_details

        self._provider_details = {}

        if self._instance:
            self._provider_details = self._instance.__dict__

        if self.user and self.identifier:
            if self.identifier:
                try:
                    self._provider_details = \
                        self.user.get_auth_providers().get(
                            module=self.module,
                            identifier=self.identifier).__dict__
                except Exception:
                    return {}
        return self._provider_details

    def __getattr__(self, key):
        if not key.startswith('get_'):
            return super(AuthProvider, self).__getattribute__(key)

        key = key.replace('get_', '')
        if key.endswith('_msg'):
            return self.get_message(key)

        if key.endswith('_policy'):
            return self.get_policy(key.replace('_policy', ''))

        if key.endswith('_url'):
            key = key.replace('_url', '')
            return self.urls.get(key)

        if key.endswith('_icon'):
            key = key.replace('_msg', '_icon')
            return settings.MEDIA_URL + self.get_message(key)

        if key.endswith('_setting'):
            key = key.replace('_setting', '')
            return self.get_message(key)

        if key.endswith('_template'):
            key = key.replace('_template', '')
            return self.get_template(key)

        return super(AuthProvider, self).__getattribute__(key)

    def is_active(self):
        return self.module_enabled

    @property
    def log_display(self):
        dsp = "%sAuth" % self.module.title()
        if self.user:
            dsp += "[%s]" % self.user.log_display
            if self.identifier:
                dsp += '[%s]' % self.identifier
                if self._instance and self._instance.pk:
                    dsp += '[%d]' % self._instance.pk
        return dsp

    def log(self, msg, *args, **kwargs):
        level = kwargs.pop('level', logging.INFO)
        message = '%s: %s' % (self.log_display, msg)
        logger.log(level, message, *args, **kwargs)


class LocalAuthProvider(AuthProvider):
    module = 'local'

    login_view = 'password_change'
    remote_authenticate = False
    username_key = 'user_email'

    messages = {
        'title': _('Classic'),
        'login_prompt': _('Classic login (username/password)'),
        'login_success': _('Logged in successfully.'),
        'method_details': 'Username: {username}',
        'logout_success_extra': ' '
    }

    policies = {
        'limit': 1,
        'switch': False
    }

    @property
    def urls(self):
        urls = super(LocalAuthProvider, self).urls
        urls['change_password'] = reverse('password_change')
        if self.user:
            urls['add'] = reverse('password_change')
        if self._instance:
            urls.update({
                'remove': reverse('remove_auth_provider',
                                  kwargs={'pk': self._instance.pk})
            })
            if 'switch' in urls:
                del urls['switch']
        return urls

    def remove_from_user(self):
        super(LocalAuthProvider, self).remove_from_user()
        self.user.set_unusable_password()
        self.user.save()


class ShibbolethAuthProvider(AuthProvider):
    module = 'shibboleth'
    login_view = 'astakos.im.views.target.shibboleth.login'
    username_key = 'provider_info_eppn'

    policies = {
        'switch': False
    }

    messages = {
        'title': _('Academic'),
        'login_description': _('If you are a student, professor or researcher'
                               ' you can login using your academic account.'),
        'add_prompt': _('Allows you to login using your Academic '
                        'account'),
        'method_details': 'Account: {username}',
        'logout_success_extra': _('You may still be logged in at your Academic'
                                  ' account though. Consider logging out '
                                  'from there too by closing all browser '
                                  'windows')
    }


class TwitterAuthProvider(AuthProvider):
    module = 'twitter'
    login_view = 'astakos.im.views.target.twitter.login'
    username_key = 'provider_info_screen_name'

    messages = {
        'title': _('Twitter'),
        'method_details': 'Screen name: {username}',
    }


class GoogleAuthProvider(AuthProvider):
    module = 'google'
    login_view = 'astakos.im.views.target.google.login'
    username_key = 'provider_info_email'

    messages = {
        'title': _('Google'),
        'method_details': 'Email: {username}',
    }


class LinkedInAuthProvider(AuthProvider):
    module = 'linkedin'
    login_view = 'astakos.im.views.target.linkedin.login'
    username_key = 'provider_info_email'

    messages = {
        'title': _('LinkedIn'),
        'method_details': 'Email: {username}',
    }


# Utility method
def get_provider(module, user_obj=None, identifier=None, **params):
    """
    Return a provider instance from the auth providers registry.
    """
    if not module in PROVIDERS:
        raise Exception('Invalid auth provider "%s"' % id)

    return PROVIDERS.get(module)(user_obj, identifier, **params)

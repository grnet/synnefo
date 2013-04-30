# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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

import hashlib
import uuid
import logging
import json
import math
import copy

from time import asctime
from datetime import datetime, timedelta
from base64 import b64encode
from urlparse import urlparse
from urllib import quote
from random import randint
from collections import defaultdict, namedtuple

from django.db import models, IntegrityError, transaction
from django.contrib.auth.models import User, UserManager, Group, Permission
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.db.models.signals import (
    pre_save, post_save, post_syncdb, post_delete)
from django.contrib.contenttypes.models import ContentType

from django.dispatch import Signal
from django.db.models import Q, Max
from django.core.urlresolvers import reverse
from django.utils.http import int_to_base36
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.safestring import mark_safe
from django.core.validators import email_re
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from astakos.im.settings import (
    DEFAULT_USER_LEVEL, INVITATIONS_PER_LEVEL,
    AUTH_TOKEN_DURATION, EMAILCHANGE_ACTIVATION_DAYS, LOGGING_LEVEL,
    SITENAME, MODERATION_ENABLED,
    PROJECT_MEMBER_JOIN_POLICIES, PROJECT_MEMBER_LEAVE_POLICIES)
from astakos.im import settings as astakos_settings
from astakos.im import auth_providers as auth

import astakos.im.messages as astakos_messages
from snf_django.lib.db.managers import ForUpdateManager
from synnefo.lib.ordereddict import OrderedDict

from snf_django.lib.db.fields import intDecimalField
from synnefo.util.text import uenc, udec
from astakos.im import presentation

logger = logging.getLogger(__name__)

DEFAULT_CONTENT_TYPE = None
_content_type = None


def get_content_type():
    global _content_type
    if _content_type is not None:
        return _content_type

    try:
        content_type = ContentType.objects.get(app_label='im',
                                               model='astakosuser')
    except:
        content_type = DEFAULT_CONTENT_TYPE
    _content_type = content_type
    return content_type

inf = float('inf')


def dict_merge(a, b):
    """
    http://www.xormedia.com/recursively-merge-dictionaries-in-python/
    """
    if not isinstance(b, dict):
        return b
    result = copy.deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
                result[k] = dict_merge(result[k], v)
        else:
            result[k] = copy.deepcopy(v)
    return result


class Service(models.Model):
    name = models.CharField(_('Name'), max_length=255, unique=True,
                            db_index=True)
    url = models.CharField(_('Service url'), max_length=255, null=True,
                           help_text=_("URL the service is accessible from"))
    api_url = models.CharField(_('Service API url'), max_length=255, null=True)
    auth_token = models.CharField(_('Authentication Token'), max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField(_('Token creation date'),
                                              null=True)
    auth_token_expires = models.DateTimeField(_('Token expiration date'),
                                              null=True)

    def renew_token(self, expiration_date=None):
        md5 = hashlib.md5()
        md5.update(self.name.encode('ascii', 'ignore'))
        md5.update(self.api_url.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        if expiration_date:
            self.auth_token_expires = expiration_date
        else:
            self.auth_token_expires = None

    def __str__(self):
        return self.name

    @classmethod
    def catalog(cls, orderfor=None):
        catalog = {}
        services = list(cls.objects.all())
        metadata = presentation.SERVICES
        metadata = dict_merge(presentation.SERVICES,
                              astakos_settings.SERVICES_META)

        for service in services:
            d = {'api_url': service.api_url,
                 'url': service.url,
                 'name': service.name}
            if service.name in metadata:
                metadata[service.name].update(d)
            else:
                metadata[service.name] = d

        def service_by_order(s):
            return s[1].get('order')

        def service_by_dashbaord_order(s):
            return s[1].get('dashboard').get('order')

        for service, info in metadata.iteritems():
            default_meta = presentation.service_defaults(service)
            base_meta = metadata.get(service, {})
            settings_meta = astakos_settings.SERVICES_META.get(service, {})
            service_meta = dict_merge(default_meta, base_meta)
            meta = dict_merge(service_meta, settings_meta)
            catalog[service] = meta

        order_key = service_by_order
        if orderfor == 'dashboard':
            order_key = service_by_dashbaord_order

        ordered_catalog = OrderedDict(sorted(catalog.iteritems(),
                                             key=order_key))
        return ordered_catalog


_presentation_data = {}
def get_presentation(resource):
    global _presentation_data
    resource_presentation = _presentation_data.get(resource, {})
    if not resource_presentation:
        resources_presentation = presentation.RESOURCES.get('resources', {})
        resource_presentation = resources_presentation.get(resource, {})
        _presentation_data[resource] = resource_presentation
    return resource_presentation

class Resource(models.Model):
    name = models.CharField(_('Name'), max_length=255, unique=True)
    desc = models.TextField(_('Description'), null=True)
    service = models.ForeignKey(Service)
    unit = models.CharField(_('Unit'), null=True, max_length=255)
    uplimit = intDecimalField(default=0)
    allow_in_projects = models.BooleanField(default=True)

    objects = ForUpdateManager()

    def __str__(self):
        return self.name

    def full_name(self):
        return str(self)

    def get_info(self):
        return {'service': str(self.service),
                'description': self.desc,
                'unit': self.unit,
                'allow_in_projects': self.allow_in_projects,
                }

    @property
    def group(self):
        default = self.name
        return get_presentation(str(self)).get('group', default)

    @property
    def help_text(self):
        default = "%s resource" % self.name
        return get_presentation(str(self)).get('help_text', default)

    @property
    def help_text_input_each(self):
        default = "%s resource" % self.name
        return get_presentation(str(self)).get('help_text_input_each', default)

    @property
    def is_abbreviation(self):
        return get_presentation(str(self)).get('is_abbreviation', False)

    @property
    def report_desc(self):
        default = "%s resource" % self.name
        return get_presentation(str(self)).get('report_desc', default)

    @property
    def placeholder(self):
        return get_presentation(str(self)).get('placeholder', self.unit)

    @property
    def verbose_name(self):
        return get_presentation(str(self)).get('verbose_name', self.name)

    @property
    def display_name(self):
        name = self.verbose_name
        if self.is_abbreviation:
            name = name.upper()
        return name

    @property
    def pluralized_display_name(self):
        if not self.unit:
            return '%ss' % self.display_name
        return self.display_name

def get_resource_names():
    _RESOURCE_NAMES = []
    resources = Resource.objects.select_related('service').all()
    _RESOURCE_NAMES = [resource.full_name() for resource in resources]
    return _RESOURCE_NAMES


class AstakosUserManager(UserManager):

    def get_auth_provider_user(self, provider, **kwargs):
        """
        Retrieve AstakosUser instance associated with the specified third party
        id.
        """
        kwargs = dict(map(lambda x: ('auth_providers__%s' % x[0], x[1]),
                          kwargs.iteritems()))
        return self.get(auth_providers__module=provider, **kwargs)

    def get_by_email(self, email):
        return self.get(email=email)

    def get_by_identifier(self, email_or_username, **kwargs):
        try:
            return self.get(email__iexact=email_or_username, **kwargs)
        except AstakosUser.DoesNotExist:
            return self.get(username__iexact=email_or_username, **kwargs)

    def user_exists(self, email_or_username, **kwargs):
        qemail = Q(email__iexact=email_or_username)
        qusername = Q(username__iexact=email_or_username)
        qextra = Q(**kwargs)
        return self.filter((qemail | qusername) & qextra).exists()

    def verified_user_exists(self, email_or_username):
        return self.user_exists(email_or_username, email_verified=True)

    def verified(self):
        return self.filter(email_verified=True)

    def uuid_catalog(self, l=None):
        """
        Returns a uuid to username mapping for the uuids appearing in l.
        If l is None returns the mapping for all existing users.
        """
        q = self.filter(uuid__in=l) if l != None else self
        return dict(q.values_list('uuid', 'username'))

    def displayname_catalog(self, l=None):
        """
        Returns a username to uuid mapping for the usernames appearing in l.
        If l is None returns the mapping for all existing users.
        """
        if l is not None:
            lmap = dict((x.lower(), x) for x in l)
            q = self.filter(username__in=lmap.keys())
            values = ((lmap[n], u) for n, u in q.values_list('username', 'uuid'))
        else:
            q = self
            values = self.values_list('username', 'uuid')
        return dict(values)



class AstakosUser(User):
    """
    Extends ``django.contrib.auth.models.User`` by defining additional fields.
    """
    affiliation = models.CharField(_('Affiliation'), max_length=255, blank=True,
                                   null=True)

    # DEPRECATED FIELDS: provider, third_party_identifier moved in
    #                    AstakosUserProvider model.
    provider = models.CharField(_('Provider'), max_length=255, blank=True,
                                null=True)
    # ex. screen_name for twitter, eppn for shibboleth
    third_party_identifier = models.CharField(_('Third-party identifier'),
                                              max_length=255, null=True,
                                              blank=True)


    #for invitations
    user_level = DEFAULT_USER_LEVEL
    level = models.IntegerField(_('Inviter level'), default=user_level)
    invitations = models.IntegerField(
        _('Invitations left'), default=INVITATIONS_PER_LEVEL.get(user_level, 0))

    auth_token = models.CharField(_('Authentication Token'),
                                  max_length=32,
                                  null=True,
                                  blank=True,
                                  help_text = _('Renew your authentication '
                                                'token. Make sure to set the new '
                                                'token in any client you may be '
                                                'using, to preserve its '
                                                'functionality.'))
    auth_token_created = models.DateTimeField(_('Token creation date'),
                                              null=True)
    auth_token_expires = models.DateTimeField(
        _('Token expiration date'), null=True)

    updated = models.DateTimeField(_('Update date'))
    is_verified = models.BooleanField(_('Is verified?'), default=False)

    email_verified = models.BooleanField(_('Email verified?'), default=False)

    has_credits = models.BooleanField(_('Has credits?'), default=False)
    has_signed_terms = models.BooleanField(
        _('I agree with the terms'), default=False)
    date_signed_terms = models.DateTimeField(
        _('Signed terms date'), null=True, blank=True)

    activation_sent = models.DateTimeField(
        _('Activation sent data'), null=True, blank=True)

    policy = models.ManyToManyField(
        Resource, null=True, through='AstakosUserQuota')

    uuid = models.CharField(max_length=255, null=True, blank=False, unique=True)

    __has_signed_terms = False
    disturbed_quota = models.BooleanField(_('Needs quotaholder syncing'),
                                           default=False, db_index=True)

    objects = AstakosUserManager()

    forupdate = ForUpdateManager()

    def __init__(self, *args, **kwargs):
        super(AstakosUser, self).__init__(*args, **kwargs)
        self.__has_signed_terms = self.has_signed_terms
        if not self.id:
            self.is_active = False

    @property
    def realname(self):
        return '%s %s' % (self.first_name, self.last_name)

    @property
    def log_display(self):
        """
        Should be used in all logger.* calls that refer to a user so that
        user display is consistent across log entries.
        """
        return '%s::%s' % (self.uuid, self.email)

    @realname.setter
    def realname(self, value):
        parts = value.split(' ')
        if len(parts) == 2:
            self.first_name = parts[0]
            self.last_name = parts[1]
        else:
            self.last_name = parts[0]

    def add_permission(self, pname):
        if self.has_perm(pname):
            return
        p, created = Permission.objects.get_or_create(
                                    codename=pname,
                                    name=pname.capitalize(),
                                    content_type=get_content_type())
        self.user_permissions.add(p)

    def remove_permission(self, pname):
        if self.has_perm(pname):
            return
        p = Permission.objects.get(codename=pname,
                                   content_type=get_content_type())
        self.user_permissions.remove(p)

    def is_project_admin(self, application_id=None):
        return self.uuid in astakos_settings.PROJECT_ADMINS

    @property
    def invitation(self):
        try:
            return Invitation.objects.get(username=self.email)
        except Invitation.DoesNotExist:
            return None

    @property
    def policies(self):
        return self.astakosuserquota_set.select_related().all()

    @policies.setter
    def policies(self, policies):
        for p in policies:
            p.setdefault('resource', '')
            p.setdefault('capacity', 0)
            p.setdefault('update', True)
            self.add_resource_policy(**p)

    def add_resource_policy(
            self, resource, capacity,
            update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(name=resource)
        if update:
            AstakosUserQuota.objects.update_or_create(
                user=self, resource=resource, defaults={
                    'capacity':capacity,
                    })
        else:
            q = self.astakosuserquota_set
            q.create(
                resource=resource, capacity=capacity,
                )

    def get_resource_policy(self, resource):
        resource = Resource.objects.get(name=resource)
        default_capacity = resource.uplimit
        try:
            policy = AstakosUserQuota.objects.get(user=self, resource=resource)
            return policy, default_capacity
        except AstakosUserQuota.DoesNotExist:
            return None, default_capacity

    def remove_resource_policy(self, service, resource):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(name=resource)
        q = self.policies.get(resource=resource).delete()

    def update_uuid(self):
        while not self.uuid:
            uuid_val =  str(uuid.uuid4())
            try:
                AstakosUser.objects.get(uuid=uuid_val)
            except AstakosUser.DoesNotExist, e:
                self.uuid = uuid_val
        return self.uuid

    def save(self, update_timestamps=True, **kwargs):
        if update_timestamps:
            if not self.id:
                self.date_joined = datetime.now()
            self.updated = datetime.now()

        # update date_signed_terms if necessary
        if self.__has_signed_terms != self.has_signed_terms:
            self.date_signed_terms = datetime.now()

        self.update_uuid()

        if self.username != self.email.lower():
            # set username
            self.username = self.email.lower()

        super(AstakosUser, self).save(**kwargs)

    def renew_token(self, flush_sessions=False, current_key=None):
        md5 = hashlib.md5()
        md5.update(settings.SECRET_KEY)
        md5.update(self.username)
        md5.update(self.realname.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        self.auth_token_expires = self.auth_token_created + \
                                  timedelta(hours=AUTH_TOKEN_DURATION)
        if flush_sessions:
            self.flush_sessions(current_key)
        msg = 'Token renewed for %s' % self.email
        logger.log(LOGGING_LEVEL, msg)

    def flush_sessions(self, current_key=None):
        q = self.sessions
        if current_key:
            q = q.exclude(session_key=current_key)

        keys = q.values_list('session_key', flat=True)
        if keys:
            msg = 'Flushing sessions: %s' % ','.join(keys)
            logger.log(LOGGING_LEVEL, msg, [])
        engine = import_module(settings.SESSION_ENGINE)
        for k in keys:
            s = engine.SessionStore(k)
            s.flush()

    def __unicode__(self):
        return '%s (%s)' % (self.realname, self.email)

    def conflicting_email(self):
        q = AstakosUser.objects.exclude(username=self.username)
        q = q.filter(email__iexact=self.email)
        if q.count() != 0:
            return True
        return False

    def email_change_is_pending(self):
        return self.emailchanges.count() > 0

    @property
    def signed_terms(self):
        term = get_latest_terms()
        if not term:
            return True
        if not self.has_signed_terms:
            return False
        if not self.date_signed_terms:
            return False
        if self.date_signed_terms < term.date:
            self.has_signed_terms = False
            self.date_signed_terms = None
            self.save()
            return False
        return True

    def set_invitations_level(self):
        """
        Update user invitation level
        """
        level = self.invitation.inviter.level + 1
        self.level = level
        self.invitations = INVITATIONS_PER_LEVEL.get(level, 0)

    def can_change_password(self):
        return self.has_auth_provider('local', auth_backend='astakos')

    def can_change_email(self):
        if not self.has_auth_provider('local'):
            return True

        local = self.get_auth_provider('local')._instance
        return local.auth_backend == 'astakos'

    # Auth providers related methods
    def get_auth_provider(self, module=None, identifier=None, **filters):
        if not module:
            return self.auth_providers.active()[0].settings

        params = {'module': module}
        if identifier:
            params['identifier'] = identifier
        params.update(filters)
        return self.auth_providers.active().get(**params).settings

    def has_auth_provider(self, provider, **kwargs):
        return bool(self.auth_providers.active().filter(module=provider,
                                                        **kwargs).count())

    def get_required_providers(self, **kwargs):
        return auth.REQUIRED_PROVIDERS.keys()

    def missing_required_providers(self):
        required = self.get_required_providers()
        missing = []
        for provider in required:
            if not self.has_auth_provider(provider):
                missing.append(auth.get_provider(provider, self))
        return missing

    def get_available_auth_providers(self, **filters):
        """
        Returns a list of providers available for add by the user.
        """
        modules = astakos_settings.IM_MODULES
        providers = []
        for p in modules:
            providers.append(auth.get_provider(p, self))
        available = []

        for p in providers:
            if p.get_add_policy:
                available.append(p)
        return available

    def get_disabled_auth_providers(self, **filters):
        providers = self.get_auth_providers(**filters)
        disabled = []
        for p in providers:
            if not p.get_login_policy:
                disabled.append(p)
        return disabled

    def get_enabled_auth_providers(self, **filters):
        providers = self.get_auth_providers(**filters)
        enabled = []
        for p in providers:
            if p.get_login_policy:
                enabled.append(p)
        return enabled

    def get_auth_providers(self, **filters):
        providers = []
        for provider in self.auth_providers.active(**filters):
            if provider.settings.module_enabled:
                providers.append(provider.settings)

        modules = astakos_settings.IM_MODULES

        def key(p):
            if not p.module in modules:
                return 100
            return modules.index(p.module)

        providers = sorted(providers, key=key)
        return providers

    # URL methods
    @property
    def auth_providers_display(self):
        return ",".join(["%s:%s" % (p.module, p.get_username_msg) for p in
                         self.get_enabled_auth_providers()])

    def add_auth_provider(self, module='local', identifier=None, **params):
        provider = auth.get_provider(module, self, identifier, **params)
        provider.add_to_user()

    def get_resend_activation_url(self):
        return reverse('send_activation', kwargs={'user_id': self.pk})

    def get_activation_url(self, nxt=False):
        url = "%s?auth=%s" % (reverse('astakos.im.views.activate'),
                                 quote(self.auth_token))
        if nxt:
            url += "&next=%s" % quote(nxt)
        return url

    def get_password_reset_url(self, token_generator=default_token_generator):
        return reverse('django.contrib.auth.views.password_reset_confirm',
                          kwargs={'uidb36':int_to_base36(self.id),
                                  'token':token_generator.make_token(self)})

    def get_inactive_message(self, provider_module, identifier=None):
        provider = self.get_auth_provider(provider_module, identifier)

        msg_extra = ''
        message = ''

        msg_inactive = provider.get_account_inactive_msg
        msg_pending = provider.get_pending_activation_msg
        msg_pending_help = _(astakos_messages.ACCOUNT_PENDING_ACTIVATION_HELP)
        #msg_resend_prompt = _(astakos_messages.ACCOUNT_RESEND_ACTIVATION)
        msg_pending_mod = provider.get_pending_moderation_msg
        msg_resend = _(astakos_messages.ACCOUNT_RESEND_ACTIVATION)

        if self.activation_sent:
            if self.email_verified:
                message = msg_inactive
            else:
                message = msg_pending
                url = self.get_resend_activation_url()
                msg_extra = msg_pending_help + \
                            u' ' + \
                            '<a href="%s">%s?</a>' % (url, msg_resend)
        else:
            if astakos_settings.MODERATION_ENABLED:
                message = msg_pending_mod
            else:
                message = msg_pending
                url = self.get_resend_activation_url()
                msg_extra = '<a href="%s">%s?</a>' % (url, \
                                msg_resend)

        return mark_safe(message + u' '+ msg_extra)

    def owns_application(self, application):
        return application.owner == self

    def owns_project(self, project):
        return project.application.owner == self

    def is_associated(self, project):
        try:
            m = ProjectMembership.objects.get(person=self, project=project)
            return m.state in ProjectMembership.ASSOCIATED_STATES
        except ProjectMembership.DoesNotExist:
            return False

    def get_membership(self, project):
        try:
            return ProjectMembership.objects.get(
                project=project,
                person=self)
        except ProjectMembership.DoesNotExist:
            return None

    def membership_display(self, project):
        m = self.get_membership(project)
        if m is None:
            return _('Not a member')
        else:
            return m.user_friendly_state_display()

    def non_owner_can_view(self, maybe_project):
        if self.is_project_admin():
            return True
        if maybe_project is None:
            return False
        project = maybe_project
        if self.is_associated(project):
            return True
        if project.is_deactivated():
            return False
        return True

    def settings(self):
        return UserSetting.objects.filter(user=self)


class AstakosUserAuthProviderManager(models.Manager):

    def active(self, **filters):
        return self.filter(active=True, **filters)

    def remove_unverified_providers(self, provider, **filters):
        try:
            existing = self.filter(module=provider, user__email_verified=False,
                                   **filters)
            for p in existing:
                p.user.delete()
        except:
            pass

    def unverified(self, provider, **filters):
        try:
            return self.get(module=provider, user__email_verified=False,
                            **filters).settings
        except AstakosUserAuthProvider.DoesNotExist:
            return None

    def verified(self, provider, **filters):
        try:
            return self.get(module=provider, user__email_verified=True,
                            **filters).settings
        except AstakosUserAuthProvider.DoesNotExist:
            return None


class AuthProviderPolicyProfileManager(models.Manager):

    def active(self):
        return self.filter(active=True)

    def for_user(self, user, provider):
        policies = {}
        exclusive_q1 = Q(provider=provider) & Q(is_exclusive=False)
        exclusive_q2 = ~Q(provider=provider) & Q(is_exclusive=True)
        exclusive_q = exclusive_q1 | exclusive_q2

        for profile in user.authpolicy_profiles.active().filter(exclusive_q):
            policies.update(profile.policies)

        user_groups = user.groups.all().values('pk')
        for profile in self.active().filter(groups__in=user_groups).filter(
                exclusive_q):
            policies.update(profile.policies)
        return policies

    def add_policy(self, name, provider, group_or_user, exclusive=False,
                   **policies):
        is_group = isinstance(group_or_user, Group)
        profile, created = self.get_or_create(name=name, provider=provider,
                                              is_exclusive=exclusive)
        profile.is_exclusive = exclusive
        profile.save()
        if is_group:
            profile.groups.add(group_or_user)
        else:
            profile.users.add(group_or_user)
        profile.set_policies(policies)
        profile.save()
        return profile


class AuthProviderPolicyProfile(models.Model):
    name = models.CharField(_('Name'), max_length=255, blank=False,
                            null=False, db_index=True)
    provider = models.CharField(_('Provider'), max_length=255, blank=False,
                                null=False)

    # apply policies to all providers excluding the one set in provider field
    is_exclusive = models.BooleanField(default=False)

    policy_add = models.NullBooleanField(null=True, default=None)
    policy_remove = models.NullBooleanField(null=True, default=None)
    policy_create = models.NullBooleanField(null=True, default=None)
    policy_login = models.NullBooleanField(null=True, default=None)
    policy_limit = models.IntegerField(null=True, default=None)
    policy_required = models.NullBooleanField(null=True, default=None)
    policy_automoderate = models.NullBooleanField(null=True, default=None)
    policy_switch = models.NullBooleanField(null=True, default=None)

    POLICY_FIELDS = ('add', 'remove', 'create', 'login', 'limit', 'required',
                     'automoderate')

    priority = models.IntegerField(null=False, default=1)
    groups = models.ManyToManyField(Group, related_name='authpolicy_profiles')
    users = models.ManyToManyField(AstakosUser,
                                   related_name='authpolicy_profiles')
    active = models.BooleanField(default=True)

    objects = AuthProviderPolicyProfileManager()

    class Meta:
        ordering = ['priority']

    @property
    def policies(self):
        policies = {}
        for pkey in self.POLICY_FIELDS:
            value = getattr(self, 'policy_%s' % pkey, None)
            if value is None:
                continue
            policies[pkey] = value
        return policies

    def set_policies(self, policies_dict):
        for key, value in policies_dict.iteritems():
            if key in self.POLICY_FIELDS:
                setattr(self, 'policy_%s' % key, value)
        return self.policies


class AstakosUserAuthProvider(models.Model):
    """
    Available user authentication methods.
    """
    affiliation = models.CharField(_('Affiliation'), max_length=255, blank=True,
                                   null=True, default=None)
    user = models.ForeignKey(AstakosUser, related_name='auth_providers')
    module = models.CharField(_('Provider'), max_length=255, blank=False,
                                default='local')
    identifier = models.CharField(_('Third-party identifier'),
                                              max_length=255, null=True,
                                              blank=True)
    active = models.BooleanField(default=True)
    auth_backend = models.CharField(_('Backend'), max_length=255, blank=False,
                                   default='astakos')
    info_data = models.TextField(default="", null=True, blank=True)
    created = models.DateTimeField('Creation date', auto_now_add=True)

    objects = AstakosUserAuthProviderManager()

    class Meta:
        unique_together = (('identifier', 'module', 'user'), )
        ordering = ('module', 'created')

    def __init__(self, *args, **kwargs):
        super(AstakosUserAuthProvider, self).__init__(*args, **kwargs)
        try:
            self.info = json.loads(self.info_data)
            if not self.info:
                self.info = {}
        except Exception, e:
            self.info = {}

        for key,value in self.info.iteritems():
            setattr(self, 'info_%s' % key, value)

    @property
    def settings(self):
        extra_data = {}

        info_data = {}
        if self.info_data:
            info_data = json.loads(self.info_data)

        extra_data['info'] = info_data

        for key in ['active', 'auth_backend', 'created', 'pk', 'affiliation']:
            extra_data[key] = getattr(self, key)

        extra_data['instance'] = self
        return auth.get_provider(self.module, self.user,
                                           self.identifier, **extra_data)

    def __repr__(self):
        return '<AstakosUserAuthProvider %s:%s>' % (self.module, self.identifier)

    def __unicode__(self):
        if self.identifier:
            return "%s:%s" % (self.module, self.identifier)
        if self.auth_backend:
            return "%s:%s" % (self.module, self.auth_backend)
        return self.module

    def save(self, *args, **kwargs):
        self.info_data = json.dumps(self.info)
        return super(AstakosUserAuthProvider, self).save(*args, **kwargs)


class ExtendedManager(models.Manager):
    def _update_or_create(self, **kwargs):
        assert kwargs, \
            'update_or_create() must be passed at least one keyword argument'
        obj, created = self.get_or_create(**kwargs)
        defaults = kwargs.pop('defaults', {})
        if created:
            return obj, True, False
        else:
            try:
                params = dict(
                    [(k, v) for k, v in kwargs.items() if '__' not in k])
                params.update(defaults)
                for attr, val in params.items():
                    if hasattr(obj, attr):
                        setattr(obj, attr, val)
                sid = transaction.savepoint()
                obj.save(force_update=True)
                transaction.savepoint_commit(sid)
                return obj, False, True
            except IntegrityError, e:
                transaction.savepoint_rollback(sid)
                try:
                    return self.get(**kwargs), False, False
                except self.model.DoesNotExist:
                    raise e

    update_or_create = _update_or_create


class AstakosUserQuota(models.Model):
    objects = ExtendedManager()
    capacity = intDecimalField()
    resource = models.ForeignKey(Resource)
    user = models.ForeignKey(AstakosUser)

    class Meta:
        unique_together = ("resource", "user")


class ApprovalTerms(models.Model):
    """
    Model for approval terms
    """

    date = models.DateTimeField(
        _('Issue date'), db_index=True, auto_now_add=True)
    location = models.CharField(_('Terms location'), max_length=255)


class Invitation(models.Model):
    """
    Model for registring invitations
    """
    inviter = models.ForeignKey(AstakosUser, related_name='invitations_sent',
                                null=True)
    realname = models.CharField(_('Real name'), max_length=255)
    username = models.CharField(_('Unique ID'), max_length=255, unique=True)
    code = models.BigIntegerField(_('Invitation code'), db_index=True)
    is_consumed = models.BooleanField(_('Consumed?'), default=False)
    created = models.DateTimeField(_('Creation date'), auto_now_add=True)
    consumed = models.DateTimeField(_('Consumption date'), null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super(Invitation, self).__init__(*args, **kwargs)
        if not self.id:
            self.code = _generate_invitation_code()

    def consume(self):
        self.is_consumed = True
        self.consumed = datetime.now()
        self.save()

    def __unicode__(self):
        return '%s -> %s [%d]' % (self.inviter, self.username, self.code)


class EmailChangeManager(models.Manager):

    @transaction.commit_on_success
    def change_email(self, activation_key):
        """
        Validate an activation key and change the corresponding
        ``User`` if valid.

        If the key is valid and has not expired, return the ``User``
        after activating.

        If the key is not valid or has expired, return ``None``.

        If the key is valid but the ``User`` is already active,
        return ``None``.

        After successful email change the activation record is deleted.

        Throws ValueError if there is already
        """
        try:
            email_change = self.model.objects.get(
                activation_key=activation_key)
            if email_change.activation_key_expired():
                email_change.delete()
                raise EmailChange.DoesNotExist
            # is there an active user with this address?
            try:
                AstakosUser.objects.get(email__iexact=email_change.new_email_address)
            except AstakosUser.DoesNotExist:
                pass
            else:
                raise ValueError(_('The new email address is reserved.'))
            # update user
            user = AstakosUser.objects.get(pk=email_change.user_id)
            old_email = user.email
            user.email = email_change.new_email_address
            user.save()
            email_change.delete()
            msg = "User %s changed email from %s to %s" % (user.log_display,
                                                           old_email,
                                                           user.email)
            logger.log(LOGGING_LEVEL, msg)
            return user
        except EmailChange.DoesNotExist:
            raise ValueError(_('Invalid activation key.'))


class EmailChange(models.Model):
    new_email_address = models.EmailField(
        _(u'new e-mail address'),
        help_text=_('Provide a new email address. Until you verify the new '
                    'address by following the activation link that will be '
                    'sent to it, your old email address will remain active.'))
    user = models.ForeignKey(
        AstakosUser, unique=True, related_name='emailchanges')
    requested_at = models.DateTimeField(auto_now_add=True)
    activation_key = models.CharField(
        max_length=40, unique=True, db_index=True)

    objects = EmailChangeManager()

    def get_url(self):
        return reverse('email_change_confirm',
                      kwargs={'activation_key': self.activation_key})

    def activation_key_expired(self):
        expiration_date = timedelta(days=EMAILCHANGE_ACTIVATION_DAYS)
        return self.requested_at + expiration_date < datetime.now()


class AdditionalMail(models.Model):
    """
    Model for registring invitations
    """
    owner = models.ForeignKey(AstakosUser)
    email = models.EmailField()


def _generate_invitation_code():
    while True:
        code = randint(1, 2L ** 63 - 1)
        try:
            Invitation.objects.get(code=code)
            # An invitation with this code already exists, try again
        except Invitation.DoesNotExist:
            return code


def get_latest_terms():
    try:
        term = ApprovalTerms.objects.order_by('-id')[0]
        return term
    except IndexError:
        pass
    return None


class PendingThirdPartyUser(models.Model):
    """
    Model for registring successful third party user authentications
    """
    third_party_identifier = models.CharField(_('Third-party identifier'), max_length=255, null=True, blank=True)
    provider = models.CharField(_('Provider'), max_length=255, blank=True)
    email = models.EmailField(_('e-mail address'), blank=True, null=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True,
                                  null=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True,
                                 null=True)
    affiliation = models.CharField('Affiliation', max_length=255, blank=True,
                                   null=True)
    username = models.CharField(_('username'), max_length=30, unique=True,
                                help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))
    token = models.CharField(_('Token'), max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    info = models.TextField(default="", null=True, blank=True)

    class Meta:
        unique_together = ("provider", "third_party_identifier")

    def get_user_instance(self):
        d = self.__dict__
        d.pop('_state', None)
        d.pop('id', None)
        d.pop('token', None)
        d.pop('created', None)
        d.pop('info', None)
        user = AstakosUser(**d)

        return user

    @property
    def realname(self):
        return '%s %s' %(self.first_name, self.last_name)

    @realname.setter
    def realname(self, value):
        parts = value.split(' ')
        if len(parts) == 2:
            self.first_name = parts[0]
            self.last_name = parts[1]
        else:
            self.last_name = parts[0]

    def save(self, **kwargs):
        if not self.id:
            # set username
            while not self.username:
                username =  uuid.uuid4().hex[:30]
                try:
                    AstakosUser.objects.get(username = username)
                except AstakosUser.DoesNotExist, e:
                    self.username = username
        super(PendingThirdPartyUser, self).save(**kwargs)

    def generate_token(self):
        self.password = self.third_party_identifier
        self.last_login = datetime.now()
        self.token = default_token_generator.make_token(self)

    def existing_user(self):
        return AstakosUser.objects.filter(auth_providers__module=self.provider,
                                         auth_providers__identifier=self.third_party_identifier)

    def get_provider(self, user):
        params = {
            'info_data': self.info,
            'affiliation': self.affiliation
        }
        return auth.get_provider(self.provider, user,
                                 self.third_party_identifier, **params)

class SessionCatalog(models.Model):
    session_key = models.CharField(_('session key'), max_length=40)
    user = models.ForeignKey(AstakosUser, related_name='sessions', null=True)


class UserSetting(models.Model):
    user = models.ForeignKey(AstakosUser)
    setting = models.CharField(max_length=255)
    value = models.IntegerField()

    objects = ForUpdateManager()

    class Meta:
        unique_together = ("user", "setting")


### PROJECTS ###
################

class ChainManager(ForUpdateManager):

    def search_by_name(self, *search_strings):
        projects = Project.objects.search_by_name(*search_strings)
        chains = [p.id for p in projects]
        apps  = ProjectApplication.objects.search_by_name(*search_strings)
        apps = (app for app in apps if app.is_latest())
        app_chains = [app.chain for app in apps if app.chain not in chains]
        return chains + app_chains

    def all_full_state(self):
        chains = self.all()
        cids = [c.chain for c in chains]
        projects = Project.objects.select_related('application').in_bulk(cids)

        objs = Chain.objects.annotate(latest=Max('chained_apps__id'))
        chain_latest = dict(objs.values_list('chain', 'latest'))

        objs = ProjectApplication.objects.select_related('applicant')
        apps = objs.in_bulk(chain_latest.values())

        d = {}
        for chain in chains:
            pk = chain.pk
            project = projects.get(pk, None)
            app = apps[chain_latest[pk]]
            d[chain.pk] = chain.get_state(project, app)

        return d

    def of_project(self, project):
        if project is None:
            return None
        try:
            return self.get(chain=project.id)
        except Chain.DoesNotExist:
            raise AssertionError('project with no chain')


class Chain(models.Model):
    chain  =   models.AutoField(primary_key=True)

    def __str__(self):
        return "%s" % (self.chain,)

    objects = ChainManager()

    PENDING            = 0
    DENIED             = 3
    DISMISSED          = 4
    CANCELLED          = 5

    APPROVED           = 10
    APPROVED_PENDING   = 11
    SUSPENDED          = 12
    SUSPENDED_PENDING  = 13
    TERMINATED         = 14
    TERMINATED_PENDING = 15

    PENDING_STATES = [PENDING,
                      APPROVED_PENDING,
                      SUSPENDED_PENDING,
                      TERMINATED_PENDING,
                      ]

    MODIFICATION_STATES = [APPROVED_PENDING,
                           SUSPENDED_PENDING,
                           TERMINATED_PENDING,
                           ]

    RELEVANT_STATES = [PENDING,
                       DENIED,
                       APPROVED,
                       APPROVED_PENDING,
                       SUSPENDED,
                       SUSPENDED_PENDING,
                       TERMINATED_PENDING,
                       ]

    SKIP_STATES = [DISMISSED,
                   CANCELLED,
                   TERMINATED]

    STATE_DISPLAY = {
        PENDING            : _("Pending"),
        DENIED             : _("Denied"),
        DISMISSED          : _("Dismissed"),
        CANCELLED          : _("Cancelled"),
        APPROVED           : _("Active"),
        APPROVED_PENDING   : _("Active - Pending"),
        SUSPENDED          : _("Suspended"),
        SUSPENDED_PENDING  : _("Suspended - Pending"),
        TERMINATED         : _("Terminated"),
        TERMINATED_PENDING : _("Terminated - Pending"),
        }


    @classmethod
    def _chain_state(cls, project_state, app_state):
        s = CHAIN_STATE.get((project_state, app_state), None)
        if s is None:
            raise AssertionError('inconsistent chain state')
        return s

    @classmethod
    def chain_state(cls, project, app):
        p_state = project.state if project else None
        return cls._chain_state(p_state, app.state)

    @classmethod
    def state_display(cls, s):
        if s is None:
            return _("Unknown")
        return cls.STATE_DISPLAY.get(s, _("Inconsistent"))

    def last_application(self):
        return self.chained_apps.order_by('-id')[0]

    def get_project(self):
        try:
            return self.chained_project
        except Project.DoesNotExist:
            return None

    def get_elements(self):
        project = self.get_project()
        app = self.last_application()
        return project, app

    def get_state(self, project, app):
        s = self.chain_state(project, app)
        return s, project, app

    def full_state(self):
        project, app = self.get_elements()
        return self.get_state(project, app)


def new_chain():
    c = Chain.objects.create()
    return c


class ProjectApplicationManager(ForUpdateManager):

    def user_visible_projects(self, *filters, **kw_filters):
        model = self.model
        return self.filter(model.Q_PENDING | model.Q_APPROVED)

    def user_visible_by_chain(self, flt):
        model = self.model
        pending = self.filter(model.Q_PENDING | model.Q_DENIED).values_list('chain')
        approved = self.filter(model.Q_APPROVED).values_list('chain')
        by_chain = dict(pending.annotate(models.Max('id')))
        by_chain.update(approved.annotate(models.Max('id')))
        return self.filter(flt, id__in=by_chain.values())

    def user_accessible_projects(self, user):
        """
        Return projects accessed by specified user.
        """
        if user.is_project_admin():
            participates_filters = Q()
        else:
            participates_filters = Q(owner=user) | Q(applicant=user) | \
                                   Q(project__projectmembership__person=user)

        return self.user_visible_by_chain(participates_filters).order_by('issue_date').distinct()

    def search_by_name(self, *search_strings):
        q = Q()
        for s in search_strings:
            q = q | Q(name__icontains=s)
        return self.filter(q)

    def latest_of_chain(self, chain_id):
        try:
            return self.filter(chain=chain_id).order_by('-id')[0]
        except IndexError:
            return None


class ProjectApplication(models.Model):
    applicant               =   models.ForeignKey(
                                    AstakosUser,
                                    related_name='projects_applied',
                                    db_index=True)

    PENDING     =    0
    APPROVED    =    1
    REPLACED    =    2
    DENIED      =    3
    DISMISSED   =    4
    CANCELLED   =    5

    state                   =   models.IntegerField(default=PENDING,
                                                    db_index=True)

    owner                   =   models.ForeignKey(
                                    AstakosUser,
                                    related_name='projects_owned',
                                    db_index=True)

    chain                   =   models.ForeignKey(Chain,
                                                  related_name='chained_apps',
                                                  db_column='chain')
    precursor_application   =   models.ForeignKey('ProjectApplication',
                                                  null=True,
                                                  blank=True)

    name                    =   models.CharField(max_length=80)
    homepage                =   models.URLField(max_length=255, null=True,
                                                verify_exists=False)
    description             =   models.TextField(null=True, blank=True)
    start_date              =   models.DateTimeField(null=True, blank=True)
    end_date                =   models.DateTimeField()
    member_join_policy      =   models.IntegerField()
    member_leave_policy     =   models.IntegerField()
    limit_on_members_number =   models.PositiveIntegerField(null=True)
    resource_grants         =   models.ManyToManyField(
                                    Resource,
                                    null=True,
                                    blank=True,
                                    through='ProjectResourceGrant')
    comments                =   models.TextField(null=True, blank=True)
    issue_date              =   models.DateTimeField(auto_now_add=True)
    response_date           =   models.DateTimeField(null=True, blank=True)
    response                =   models.TextField(null=True, blank=True)

    objects                 =   ProjectApplicationManager()

    # Compiled queries
    Q_PENDING  = Q(state=PENDING)
    Q_APPROVED = Q(state=APPROVED)
    Q_DENIED   = Q(state=DENIED)

    class Meta:
        unique_together = ("chain", "id")

    def __unicode__(self):
        return "%s applied by %s" % (self.name, self.applicant)

    # TODO: Move to a more suitable place
    APPLICATION_STATE_DISPLAY = {
        PENDING  : _('Pending review'),
        APPROVED : _('Approved'),
        REPLACED : _('Replaced'),
        DENIED   : _('Denied'),
        DISMISSED: _('Dismissed'),
        CANCELLED: _('Cancelled')
    }

    @property
    def log_display(self):
        return "application %s (%s) for project %s" % (
            self.id, self.name, self.chain)

    def get_project(self):
        try:
            project = Project.objects.get(id=self.chain, state=Project.APPROVED)
            return Project
        except Project.DoesNotExist, e:
            return None

    def state_display(self):
        return self.APPLICATION_STATE_DISPLAY.get(self.state, _('Unknown'))

    def project_state_display(self):
        try:
            project = self.project
            return project.state_display()
        except Project.DoesNotExist:
            return self.state_display()

    def add_resource_policy(self, service, resource, uplimit):
        """Raises ObjectDoesNotExist, IntegrityError"""
        q = self.projectresourcegrant_set
        resource = Resource.objects.get(name=resource)
        q.create(resource=resource, member_capacity=uplimit)

    def members_count(self):
        return self.project.approved_memberships.count()

    @property
    def grants(self):
        return self.projectresourcegrant_set.values('member_capacity',
                                                    'resource__name')

    @property
    def resource_policies(self):
        return [str(rp) for rp in self.projectresourcegrant_set.all()]

    @resource_policies.setter
    def resource_policies(self, policies):
        for p in policies:
            service = p.get('service', None)
            resource = p.get('resource', None)
            uplimit = p.get('uplimit', 0)
            self.add_resource_policy(service, resource, uplimit)

    def pending_modifications_incl_me(self):
        q = self.chained_applications()
        q = q.filter(Q(state=self.PENDING))
        return q

    def last_pending_incl_me(self):
        try:
            return self.pending_modifications_incl_me().order_by('-id')[0]
        except IndexError:
            return None

    def pending_modifications(self):
        return self.pending_modifications_incl_me().filter(~Q(id=self.id))

    def last_pending(self):
        try:
            return self.pending_modifications().order_by('-id')[0]
        except IndexError:
            return None

    def is_modification(self):
        # if self.state != self.PENDING:
        #     return False
        parents = self.chained_applications().filter(id__lt=self.id)
        parents = parents.filter(state__in=[self.APPROVED])
        return parents.count() > 0

    def chained_applications(self):
        return ProjectApplication.objects.filter(chain=self.chain)

    def is_latest(self):
        return self.chained_applications().order_by('-id')[0] == self

    def has_pending_modifications(self):
        return bool(self.last_pending())

    def denied_modifications(self):
        q = self.chained_applications()
        q = q.filter(Q(state=self.DENIED))
        q = q.filter(~Q(id=self.id))
        return q

    def last_denied(self):
        try:
            return self.denied_modifications().order_by('-id')[0]
        except IndexError:
            return None

    def has_denied_modifications(self):
        return bool(self.last_denied())

    def is_applied(self):
        try:
            self.project
            return True
        except Project.DoesNotExist:
            return False

    def get_project(self):
        try:
            return Project.objects.get(id=self.chain)
        except Project.DoesNotExist:
            return None

    def project_exists(self):
        return self.get_project() is not None

    def _get_project_for_update(self):
        try:
            objects = Project.objects
            project = objects.get_for_update(id=self.chain)
            return project
        except Project.DoesNotExist:
            return None

    def can_cancel(self):
        return self.state == self.PENDING

    def cancel(self):
        if not self.can_cancel():
            m = _("cannot cancel: application '%s' in state '%s'") % (
                    self.id, self.state)
            raise AssertionError(m)

        self.state = self.CANCELLED
        self.save()

    def can_dismiss(self):
        return self.state == self.DENIED

    def dismiss(self):
        if not self.can_dismiss():
            m = _("cannot dismiss: application '%s' in state '%s'") % (
                    self.id, self.state)
            raise AssertionError(m)

        self.state = self.DISMISSED
        self.save()

    def can_deny(self):
        return self.state == self.PENDING

    def deny(self, reason):
        if not self.can_deny():
            m = _("cannot deny: application '%s' in state '%s'") % (
                    self.id, self.state)
            raise AssertionError(m)

        self.state = self.DENIED
        self.response_date = datetime.now()
        self.response = reason
        self.save()

    def can_approve(self):
        return self.state == self.PENDING

    def approve(self, approval_user=None):
        """
        If approval_user then during owner membership acceptance
        it is checked whether the request_user is eligible.

        Raises:
            PermissionDenied
        """

        if not transaction.is_managed():
            raise AssertionError("NOPE")

        new_project_name = self.name
        if not self.can_approve():
            m = _("cannot approve: project '%s' in state '%s'") % (
                    new_project_name, self.state)
            raise AssertionError(m) # invalid argument

        now = datetime.now()
        project = self._get_project_for_update()

        try:
            q = Q(name=new_project_name) & ~Q(state=Project.TERMINATED)
            conflicting_project = Project.objects.get(q)
            if (conflicting_project != project):
                m = (_("cannot approve: project with name '%s' "
                       "already exists (id: %s)") % (
                        new_project_name, conflicting_project.id))
                raise PermissionDenied(m) # invalid argument
        except Project.DoesNotExist:
            pass

        new_project = False
        if project is None:
            new_project = True
            project = Project(id=self.chain)

        project.name = new_project_name
        project.application = self
        project.last_approval_date = now

        project.save()

        self.state = self.APPROVED
        self.response_date = now
        self.save()
        return project

    @property
    def member_join_policy_display(self):
        return PROJECT_MEMBER_JOIN_POLICIES.get(str(self.member_join_policy))

    @property
    def member_leave_policy_display(self):
        return PROJECT_MEMBER_LEAVE_POLICIES.get(str(self.member_leave_policy))

class ProjectResourceGrant(models.Model):

    resource                =   models.ForeignKey(Resource)
    project_application     =   models.ForeignKey(ProjectApplication,
                                                  null=True)
    project_capacity        =   intDecimalField(null=True)
    member_capacity         =   intDecimalField(default=0)

    objects = ExtendedManager()

    class Meta:
        unique_together = ("resource", "project_application")

    def display_member_capacity(self):
        if self.member_capacity:
            if self.resource.unit:
                return ProjectResourceGrant.display_filesize(
                    self.member_capacity)
            else:
                if math.isinf(self.member_capacity):
                    return 'Unlimited'
                else:
                    return self.member_capacity
        else:
            return 'Unlimited'

    def __str__(self):
        return 'Max %s per user: %s' % (self.resource.pluralized_display_name,
                                        self.display_member_capacity())

    @classmethod
    def display_filesize(cls, value):
        try:
            value = float(value)
        except:
            return
        else:
            if math.isinf(value):
                return 'Unlimited'
            if value > 1:
                unit_list = zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'],
                                [0, 0, 0, 0, 0, 0])
                exponent = min(int(math.log(value, 1024)), len(unit_list) - 1)
                quotient = float(value) / 1024**exponent
                unit, value_decimals = unit_list[exponent]
                format_string = '{0:.%sf} {1}' % (value_decimals)
                return format_string.format(quotient, unit)
            if value == 0:
                return '0 bytes'
            if value == 1:
                return '1 byte'
            else:
               return '0'


class ProjectManager(ForUpdateManager):

    def terminated_projects(self):
        q = self.model.Q_TERMINATED
        return self.filter(q)

    def not_terminated_projects(self):
        q = ~self.model.Q_TERMINATED
        return self.filter(q)

    def deactivated_projects(self):
        q = self.model.Q_DEACTIVATED
        return self.filter(q)

    def expired_projects(self):
        q = (~Q(state=Project.TERMINATED) &
              Q(application__end_date__lt=datetime.now()))
        return self.filter(q)

    def search_by_name(self, *search_strings):
        q = Q()
        for s in search_strings:
            q = q | Q(name__icontains=s)
        return self.filter(q)


class Project(models.Model):

    id                          =   models.OneToOneField(Chain,
                                                      related_name='chained_project',
                                                      db_column='id',
                                                      primary_key=True)

    application                 =   models.OneToOneField(
                                            ProjectApplication,
                                            related_name='project')
    last_approval_date          =   models.DateTimeField(null=True)

    members                     =   models.ManyToManyField(
                                            AstakosUser,
                                            through='ProjectMembership')

    deactivation_reason         =   models.CharField(max_length=255, null=True)
    deactivation_date           =   models.DateTimeField(null=True)

    creation_date               =   models.DateTimeField(auto_now_add=True)
    name                        =   models.CharField(
                                            max_length=80,
                                            null=True,
                                            db_index=True,
                                            unique=True)

    APPROVED    = 1
    SUSPENDED   = 10
    TERMINATED  = 100

    state                       =   models.IntegerField(default=APPROVED,
                                                        db_index=True)

    objects     =   ProjectManager()

    # Compiled queries
    Q_TERMINATED  = Q(state=TERMINATED)
    Q_SUSPENDED   = Q(state=SUSPENDED)
    Q_DEACTIVATED = Q_TERMINATED | Q_SUSPENDED

    def __str__(self):
        return uenc(_("<project %s '%s'>") %
                    (self.id, udec(self.application.name)))

    __repr__ = __str__

    def __unicode__(self):
        return _("<project %s '%s'>") % (self.id, self.application.name)

    STATE_DISPLAY = {
        APPROVED   : 'Active',
        SUSPENDED  : 'Suspended',
        TERMINATED : 'Terminated'
        }

    def state_display(self):
        return self.STATE_DISPLAY.get(self.state, _('Unknown'))

    def expiration_info(self):
        return (str(self.id), self.name, self.state_display(),
                str(self.application.end_date))

    def is_deactivated(self, reason=None):
        if reason is not None:
            return self.state == reason

        return self.state != self.APPROVED

    ### Deactivation calls

    def terminate(self):
        self.deactivation_reason = 'TERMINATED'
        self.deactivation_date = datetime.now()
        self.state = self.TERMINATED
        self.name = None
        self.save()

    def suspend(self):
        self.deactivation_reason = 'SUSPENDED'
        self.deactivation_date = datetime.now()
        self.state = self.SUSPENDED
        self.save()

    def resume(self):
        self.deactivation_reason = None
        self.deactivation_date = None
        self.state = self.APPROVED
        self.save()

    ### Logical checks

    def is_inconsistent(self):
        now = datetime.now()
        dates = [self.creation_date,
                 self.last_approval_date,
                 self.deactivation_date]
        return any([date > now for date in dates])

    def is_approved(self):
        return self.state == self.APPROVED

    @property
    def is_alive(self):
        return not self.is_terminated

    @property
    def is_terminated(self):
        return self.is_deactivated(self.TERMINATED)

    @property
    def is_suspended(self):
        return self.is_deactivated(self.SUSPENDED)

    def violates_resource_grants(self):
        return False

    def violates_members_limit(self, adding=0):
        application = self.application
        limit = application.limit_on_members_number
        if limit is None:
            return False
        return (len(self.approved_members) + adding > limit)


    ### Other

    def count_pending_memberships(self):
        memb_set = self.projectmembership_set
        memb_count = memb_set.filter(state=ProjectMembership.REQUESTED).count()
        return memb_count

    def members_count(self):
        return self.approved_memberships.count()

    @property
    def approved_memberships(self):
        query = ProjectMembership.Q_ACCEPTED_STATES
        return self.projectmembership_set.filter(query)

    @property
    def approved_members(self):
        return [m.person for m in self.approved_memberships]

    def add_member(self, user):
        """
        Raises:
            django.exceptions.PermissionDenied
            astakos.im.models.AstakosUser.DoesNotExist
        """
        if isinstance(user, (int, long)):
            user = AstakosUser.objects.get(user=user)

        m, created = ProjectMembership.objects.get_or_create(
            person=user, project=self
        )
        m.accept()

    def remove_member(self, user):
        """
        Raises:
            django.exceptions.PermissionDenied
            astakos.im.models.AstakosUser.DoesNotExist
            astakos.im.models.ProjectMembership.DoesNotExist
        """
        if isinstance(user, (int, long)):
            user = AstakosUser.objects.get(user=user)

        m = ProjectMembership.objects.get(person=user, project=self)
        m.remove()


CHAIN_STATE = {
    (Project.APPROVED,   ProjectApplication.PENDING)  : Chain.APPROVED_PENDING,
    (Project.APPROVED,   ProjectApplication.APPROVED) : Chain.APPROVED,
    (Project.APPROVED,   ProjectApplication.DENIED)   : Chain.APPROVED,
    (Project.APPROVED,   ProjectApplication.DISMISSED): Chain.APPROVED,
    (Project.APPROVED,   ProjectApplication.CANCELLED): Chain.APPROVED,

    (Project.SUSPENDED,  ProjectApplication.PENDING)  : Chain.SUSPENDED_PENDING,
    (Project.SUSPENDED,  ProjectApplication.APPROVED) : Chain.SUSPENDED,
    (Project.SUSPENDED,  ProjectApplication.DENIED)   : Chain.SUSPENDED,
    (Project.SUSPENDED,  ProjectApplication.DISMISSED): Chain.SUSPENDED,
    (Project.SUSPENDED,  ProjectApplication.CANCELLED): Chain.SUSPENDED,

    (Project.TERMINATED, ProjectApplication.PENDING)  : Chain.TERMINATED_PENDING,
    (Project.TERMINATED, ProjectApplication.APPROVED) : Chain.TERMINATED,
    (Project.TERMINATED, ProjectApplication.DENIED)   : Chain.TERMINATED,
    (Project.TERMINATED, ProjectApplication.DISMISSED): Chain.TERMINATED,
    (Project.TERMINATED, ProjectApplication.CANCELLED): Chain.TERMINATED,

    (None,               ProjectApplication.PENDING)  : Chain.PENDING,
    (None,               ProjectApplication.DENIED)   : Chain.DENIED,
    (None,               ProjectApplication.DISMISSED): Chain.DISMISSED,
    (None,               ProjectApplication.CANCELLED): Chain.CANCELLED,
    }


class ProjectMembershipManager(ForUpdateManager):

    def any_accepted(self):
        q = self.model.Q_ACTUALLY_ACCEPTED
        return self.filter(q)

    def actually_accepted(self):
        q = self.model.Q_ACTUALLY_ACCEPTED
        return self.filter(q)

    def requested(self):
        return self.filter(state=ProjectMembership.REQUESTED)

    def suspended(self):
        return self.filter(state=ProjectMembership.USER_SUSPENDED)

class ProjectMembership(models.Model):

    person              =   models.ForeignKey(AstakosUser)
    request_date        =   models.DateField(auto_now_add=True)
    project             =   models.ForeignKey(Project)

    REQUESTED           =   0
    ACCEPTED            =   1
    LEAVE_REQUESTED     =   5
    # User deactivation
    USER_SUSPENDED      =   10

    REMOVED             =   200

    ASSOCIATED_STATES   =   set([REQUESTED,
                                 ACCEPTED,
                                 LEAVE_REQUESTED,
                                 USER_SUSPENDED,
                                 ])

    ACCEPTED_STATES     =   set([ACCEPTED,
                                 LEAVE_REQUESTED,
                                 USER_SUSPENDED,
                                 ])

    ACTUALLY_ACCEPTED   =   set([ACCEPTED, LEAVE_REQUESTED])

    state               =   models.IntegerField(default=REQUESTED,
                                                db_index=True)
    acceptance_date     =   models.DateField(null=True, db_index=True)
    leave_request_date  =   models.DateField(null=True)

    objects     =   ProjectMembershipManager()

    # Compiled queries
    Q_ACCEPTED_STATES = ~Q(state=REQUESTED) & ~Q(state=REMOVED)
    Q_ACTUALLY_ACCEPTED = Q(state=ACCEPTED) | Q(state=LEAVE_REQUESTED)

    MEMBERSHIP_STATE_DISPLAY = {
        REQUESTED           : _('Requested'),
        ACCEPTED            : _('Accepted'),
        LEAVE_REQUESTED     : _('Leave Requested'),
        USER_SUSPENDED      : _('Suspended'),
        REMOVED             : _('Pending removal'),
        }

    USER_FRIENDLY_STATE_DISPLAY = {
        REQUESTED           : _('Join requested'),
        ACCEPTED            : _('Accepted member'),
        LEAVE_REQUESTED     : _('Requested to leave'),
        USER_SUSPENDED      : _('Suspended member'),
        REMOVED             : _('Pending removal'),
        }

    def state_display(self):
        return self.MEMBERSHIP_STATE_DISPLAY.get(self.state, _('Unknown'))

    def user_friendly_state_display(self):
        return self.USER_FRIENDLY_STATE_DISPLAY.get(self.state, _('Unknown'))

    class Meta:
        unique_together = ("person", "project")
        #index_together = [["project", "state"]]

    def __str__(self):
        return uenc(_("<'%s' membership in '%s'>") % (
                self.person.username, self.project))

    __repr__ = __str__

    def __init__(self, *args, **kwargs):
        self.state = self.REQUESTED
        super(ProjectMembership, self).__init__(*args, **kwargs)

    def _set_history_item(self, reason, date=None):
        if isinstance(reason, basestring):
            reason = ProjectMembershipHistory.reasons.get(reason, -1)

        history_item = ProjectMembershipHistory(
                            serial=self.id,
                            person=self.person_id,
                            project=self.project_id,
                            date=date or datetime.now(),
                            reason=reason)
        history_item.save()
        serial = history_item.id

    def can_accept(self):
        return self.state == self.REQUESTED

    def accept(self):
        if not self.can_accept():
            m = _("%s: attempt to accept in state '%s'") % (self, self.state)
            raise AssertionError(m)

        now = datetime.now()
        self.acceptance_date = now
        self._set_history_item(reason='ACCEPT', date=now)
        self.state = self.ACCEPTED
        self.save()

    def can_leave(self):
        return self.state in self.ACCEPTED_STATES

    def leave_request(self):
        if not self.can_leave():
            m = _("%s: attempt to request to leave in state '%s'") % (
                self, self.state)
            raise AssertionError(m)

        self.leave_request_date = datetime.now()
        self.state = self.LEAVE_REQUESTED
        self.save()

    def can_deny_leave(self):
        return self.state == self.LEAVE_REQUESTED

    def leave_request_deny(self):
        if not self.can_deny_leave():
            m = _("%s: attempt to deny leave request in state '%s'") % (
                self, self.state)
            raise AssertionError(m)

        self.leave_request_date = None
        self.state = self.ACCEPTED
        self.save()

    def can_cancel_leave(self):
        return self.state == self.LEAVE_REQUESTED

    def leave_request_cancel(self):
        if not self.can_cancel_leave():
            m = _("%s: attempt to cancel leave request in state '%s'") % (
                self, self.state)
            raise AssertionError(m)

        self.leave_request_date = None
        self.state = self.ACCEPTED
        self.save()

    def can_remove(self):
        return self.state in self.ACCEPTED_STATES

    def remove(self):
        if not self.can_remove():
            m = _("%s: attempt to remove in state '%s'") % (self, self.state)
            raise AssertionError(m)

        self._set_history_item(reason='REMOVE')
        self.delete()

    def can_reject(self):
        return self.state == self.REQUESTED

    def reject(self):
        if not self.can_reject():
            m = _("%s: attempt to reject in state '%s'") % (self, self.state)
            raise AssertionError(m)

        # rejected requests don't need sync,
        # because they were never effected
        self._set_history_item(reason='REJECT')
        self.delete()

    def can_cancel(self):
        return self.state == self.REQUESTED

    def cancel(self):
        if not self.can_cancel():
            m = _("%s: attempt to cancel in state '%s'") % (self, self.state)
            raise AssertionError(m)

        # rejected requests don't need sync,
        # because they were never effected
        self._set_history_item(reason='CANCEL')
        self.delete()


class Serial(models.Model):
    serial  =   models.AutoField(primary_key=True)


class ProjectMembershipHistory(models.Model):
    reasons_list    =   ['ACCEPT', 'REJECT', 'REMOVE']
    reasons         =   dict((k, v) for v, k in enumerate(reasons_list))

    person  =   models.BigIntegerField()
    project =   models.BigIntegerField()
    date    =   models.DateField(auto_now_add=True)
    reason  =   models.IntegerField()
    serial  =   models.BigIntegerField()

### SIGNALS ###
################

def create_astakos_user(u):
    try:
        AstakosUser.objects.get(user_ptr=u.pk)
    except AstakosUser.DoesNotExist:
        extended_user = AstakosUser(user_ptr_id=u.pk)
        extended_user.__dict__.update(u.__dict__)
        extended_user.save()
        if not extended_user.has_auth_provider('local'):
            extended_user.add_auth_provider('local')
    except BaseException, e:
        logger.exception(e)

def fix_superusers():
    # Associate superusers with AstakosUser
    admins = User.objects.filter(is_superuser=True)
    for u in admins:
        create_astakos_user(u)

def user_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    create_astakos_user(instance)
post_save.connect(user_post_save, sender=User)

def astakosuser_post_save(sender, instance, created, **kwargs):
    pass

post_save.connect(astakosuser_post_save, sender=AstakosUser)

def resource_post_save(sender, instance, created, **kwargs):
    pass

post_save.connect(resource_post_save, sender=Resource)

def renew_token(sender, instance, **kwargs):
    if not instance.auth_token:
        instance.renew_token()
pre_save.connect(renew_token, sender=AstakosUser)
pre_save.connect(renew_token, sender=Service)

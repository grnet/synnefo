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

import hashlib
import uuid
import logging
import json

from time import asctime, sleep
from datetime import datetime, timedelta
from base64 import b64encode
from urlparse import urlparse
from urllib import quote
from random import randint
from collections import defaultdict, namedtuple

from django.db import models, IntegrityError, transaction, connection
from django.contrib.auth.models import User, UserManager, Group, Permission
from django.utils.translation import ugettext as _
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models.signals import (
    pre_save, post_save, post_syncdb, post_delete)
from django.contrib.contenttypes.models import ContentType

from django.dispatch import Signal
from django.db.models import Q
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
    SITENAME, SERVICES, MODERATION_ENABLED, RESOURCES_PRESENTATION_DATA)
from astakos.im import settings as astakos_settings
from astakos.im.endpoints.qh import (
    register_users, register_resources, qh_add_quota, QuotaLimits,
    qh_query_serials, qh_ack_serials)
from astakos.im import auth_providers

import astakos.im.messages as astakos_messages
from .managers import ForUpdateManager

from synnefo.lib.quotaholder.api import QH_PRACTICALLY_INFINITE
from synnefo.lib.db.intdecimalfield import intDecimalField

logger = logging.getLogger(__name__)

DEFAULT_CONTENT_TYPE = None
_content_type = None

def get_content_type():
    global _content_type
    if _content_type is not None:
        return _content_type

    try:
        content_type = ContentType.objects.get(app_label='im', model='astakosuser')
    except:
        content_type = DEFAULT_CONTENT_TYPE
    _content_type = content_type
    return content_type

RESOURCE_SEPARATOR = '.'

inf = float('inf')

class Service(models.Model):
    name = models.CharField(_('Name'), max_length=255, unique=True, db_index=True)
    url = models.FilePathField()
    icon = models.FilePathField(blank=True)
    auth_token = models.CharField(_('Authentication Token'), max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField(_('Token creation date'), null=True)
    auth_token_expires = models.DateTimeField(
        _('Token expiration date'), null=True)

    def renew_token(self, expiration_date=None):
        md5 = hashlib.md5()
        md5.update(self.name.encode('ascii', 'ignore'))
        md5.update(self.url.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        if expiration_date:
            self.auth_token_expires = expiration_date
        else:
            self.auth_token_expires = None

    def __str__(self):
        return self.name

    @property
    def resources(self):
        return self.resource_set.all()

    @resources.setter
    def resources(self, resources):
        for s in resources:
            self.resource_set.create(**s)

    def add_resource(self, service, resource, uplimit, update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(service__name=service, name=resource)
        if update:
            AstakosUserQuota.objects.update_or_create(user=self,
                                                      resource=resource,
                                                      defaults={'uplimit': uplimit})
        else:
            q = self.astakosuserquota_set
            q.create(resource=resource, uplimit=uplimit)


class ResourceMetadata(models.Model):
    key = models.CharField(_('Name'), max_length=255, unique=True, db_index=True)
    value = models.CharField(_('Value'), max_length=255)

_presentation_data = {}
def get_presentation(resource):
    global _presentation_data
    presentation = _presentation_data.get(resource, {})
    if not presentation:
        resource_presentation = RESOURCES_PRESENTATION_DATA.get('resources', {})
        presentation = resource_presentation.get(resource, {})
        _presentation_data[resource] = presentation
    return presentation

class Resource(models.Model):
    name = models.CharField(_('Name'), max_length=255)
    meta = models.ManyToManyField(ResourceMetadata)
    service = models.ForeignKey(Service)
    desc = models.TextField(_('Description'), null=True)
    unit = models.CharField(_('Name'), null=True, max_length=255)
    group = models.CharField(_('Group'), null=True, max_length=255)

    class Meta:
        unique_together = ("name", "service")

    def __str__(self):
        return '%s%s%s' % (self.service, RESOURCE_SEPARATOR, self.name)

    @property
    def help_text(self):
        return get_presentation(str(self)).get('help_text', '')

    @property
    def help_text_input_each(self):
        return get_presentation(str(self)).get('help_text_input_each', '')

    @property
    def is_abbreviation(self):
        return get_presentation(str(self)).get('is_abbreviation', False)

    @property
    def report_desc(self):
        return get_presentation(str(self)).get('report_desc', '')

    @property
    def placeholder(self):
        return get_presentation(str(self)).get('placeholder', '')

    @property
    def verbose_name(self):
        return get_presentation(str(self)).get('verbose_name', '')


_default_quota = {}
def get_default_quota():
    global _default_quota
    if _default_quota:
        return _default_quota
    for s, data in SERVICES.iteritems():
        map(
            lambda d:_default_quota.update(
                {'%s%s%s' % (s, RESOURCE_SEPARATOR, d.get('name')):d.get('uplimit', 0)}
            ),
            data.get('resources', {})
        )
    return _default_quota

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
        return self.filter(qemail | qusername).exists()


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

    auth_token = models.CharField(_('Authentication Token'), max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField(_('Token creation date'), null=True)
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

    def __init__(self, *args, **kwargs):
        super(AstakosUser, self).__init__(*args, **kwargs)
        self.__has_signed_terms = self.has_signed_terms
        if not self.id:
            self.is_active = False

    @property
    def realname(self):
        return '%s %s' % (self.first_name, self.last_name)

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

    @property
    def invitation(self):
        try:
            return Invitation.objects.get(username=self.email)
        except Invitation.DoesNotExist:
            return None

    @property
    def quota(self):
        """Returns a dict with the sum of quota limits per resource"""
        d = defaultdict(int)
        default_quota = get_default_quota()
        d.update(default_quota)
        for q in self.policies:
            d[q.resource] += q.uplimit or inf
        for m in self.projectmembership_set.select_related().all():
            if not m.acceptance_date:
                continue
            p = m.project
            if not p.is_active():
                continue
            grants = p.application.projectresourcegrant_set.all()
            for g in grants:
                d[str(g.resource)] += g.member_capacity or inf
        return d

    @property
    def policies(self):
        return self.astakosuserquota_set.select_related().all()

    @policies.setter
    def policies(self, policies):
        for p in policies:
            service = policies.get('service', None)
            resource = policies.get('resource', None)
            uplimit = policies.get('uplimit', 0)
            update = policies.get('update', True)
            self.add_policy(service, resource, uplimit, update)

    def add_policy(self, service, resource, uplimit, update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(service__name=service, name=resource)
        if update:
            AstakosUserQuota.objects.update_or_create(user=self,
                                                      resource=resource,
                                                      defaults={'uplimit': uplimit})
        else:
            q = self.astakosuserquota_set
            q.create(resource=resource, uplimit=uplimit)

    def remove_policy(self, service, resource):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(service__name=service, name=resource)
        q = self.policies.get(resource=resource).delete()

    def update_uuid(self):
        while not self.uuid:
            uuid_val =  str(uuid.uuid4())
            try:
                AstakosUser.objects.get(uuid=uuid_val)
            except AstakosUser.DoesNotExist, e:
                self.uuid = uuid_val
        return self.uuid

    @property
    def extended_groups(self):
        return self.membership_set.select_related().all()

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

        self.validate_unique_email_isactive()

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

    def validate_unique_email_isactive(self):
        """
        Implements a unique_together constraint for email and is_active fields.
        """
        q = AstakosUser.objects.all()
        q = q.filter(email = self.email)
        if self.id:
            q = q.filter(~Q(id = self.id))
        if q.count() != 0:
            m = 'Another account with the same email = %(email)s & \
                is_active = %(is_active)s found.' % self.__dict__
            raise ValidationError(m)

    def email_change_is_pending(self):
        return self.emailchanges.count() > 0

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

    def can_login_with_auth_provider(self, provider):
        if not self.has_auth_provider(provider):
            return False
        else:
            return auth_providers.get_provider(provider).is_available_for_login()

    def can_add_auth_provider(self, provider, **kwargs):
        provider_settings = auth_providers.get_provider(provider)

        if not provider_settings.is_available_for_add():
            return False

        if self.has_auth_provider(provider) and \
           provider_settings.one_per_user:
            return False

        if 'provider_info' in kwargs:
            kwargs.pop('provider_info')

        if 'identifier' in kwargs:
            try:
                # provider with specified params already exist
                existing_user = AstakosUser.objects.get_auth_provider_user(provider,
                                                                   **kwargs)
            except AstakosUser.DoesNotExist:
                return True
            else:
                return False

        return True

    def can_remove_auth_provider(self, module):
        provider = auth_providers.get_provider(module)
        existing = self.get_active_auth_providers()
        existing_for_provider = self.get_active_auth_providers(module=module)

        if len(existing) <= 1:
            return False

        if len(existing_for_provider) == 1 and provider.is_required():
            return False

        return True

    def can_change_password(self):
        return self.has_auth_provider('local', auth_backend='astakos')

    def has_required_auth_providers(self):
        required = auth_providers.REQUIRED_PROVIDERS
        for provider in required:
            if not self.has_auth_provider(provider):
                return False
        return True

    def has_auth_provider(self, provider, **kwargs):
        return bool(self.auth_providers.filter(module=provider,
                                               **kwargs).count())

    def add_auth_provider(self, provider, **kwargs):
        info_data = ''
        if 'provider_info' in kwargs:
            info_data = kwargs.pop('provider_info')
            if isinstance(info_data, dict):
                info_data = json.dumps(info_data)

        if self.can_add_auth_provider(provider, **kwargs):
            self.auth_providers.create(module=provider, active=True,
                                       info_data=info_data,
                                       **kwargs)
        else:
            raise Exception('Cannot add provider')

    def add_pending_auth_provider(self, pending):
        """
        Convert PendingThirdPartyUser object to AstakosUserAuthProvider entry for
        the current user.
        """
        if not isinstance(pending, PendingThirdPartyUser):
            pending = PendingThirdPartyUser.objects.get(token=pending)

        provider = self.add_auth_provider(pending.provider,
                               identifier=pending.third_party_identifier,
                                affiliation=pending.affiliation,
                                          provider_info=pending.info)

        if email_re.match(pending.email or '') and pending.email != self.email:
            self.additionalmail_set.get_or_create(email=pending.email)

        pending.delete()
        return provider

    def remove_auth_provider(self, provider, **kwargs):
        self.auth_providers.get(module=provider, **kwargs).delete()

    # user urls
    def get_resend_activation_url(self):
        return reverse('send_activation', kwargs={'user_id': self.pk})

    def get_provider_remove_url(self, module, **kwargs):
        return reverse('remove_auth_provider', kwargs={
            'pk': self.auth_providers.get(module=module, **kwargs).pk})

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

    def get_auth_providers(self):
        return self.auth_providers.all()

    def get_available_auth_providers(self):
        """
        Returns a list of providers available for user to connect to.
        """
        providers = []
        for module, provider_settings in auth_providers.PROVIDERS.iteritems():
            if self.can_add_auth_provider(module):
                providers.append(provider_settings(self))

        return providers

    def get_active_auth_providers(self, **filters):
        providers = []
        for provider in self.auth_providers.active(**filters):
            if auth_providers.get_provider(provider.module).is_available_for_login():
                providers.append(provider)
        return providers

    @property
    def auth_providers_display(self):
        return ",".join(map(lambda x:unicode(x), self.auth_providers.active()))

    def get_inactive_message(self):
        msg_extra = ''
        message = ''
        if self.activation_sent:
            if self.email_verified:
                message = _(astakos_messages.ACCOUNT_INACTIVE)
            else:
                message = _(astakos_messages.ACCOUNT_PENDING_ACTIVATION)
                if astakos_settings.MODERATION_ENABLED:
                    msg_extra = _(astakos_messages.ACCOUNT_PENDING_ACTIVATION_HELP)
                else:
                    url = self.get_resend_activation_url()
                    msg_extra = mark_safe(_(astakos_messages.ACCOUNT_PENDING_ACTIVATION_HELP) + \
                                u' ' + \
                                _('<a href="%s">%s?</a>') % (url,
                                _(astakos_messages.ACCOUNT_RESEND_ACTIVATION_PROMPT)))
        else:
            if astakos_settings.MODERATION_ENABLED:
                message = _(astakos_messages.ACCOUNT_PENDING_MODERATION)
            else:
                message = astakos_messages.ACCOUNT_PENDING_ACTIVATION
                url = self.get_resend_activation_url()
                msg_extra = mark_safe(_('<a href="%s">%s?</a>') % (url,
                            _(astakos_messages.ACCOUNT_RESEND_ACTIVATION_PROMPT)))

        return mark_safe(message + u' '+ msg_extra)

    def owns_project(self, project):
        return project.user_status(self) == 100

    def is_project_member(self, project):
        return project.user_status(self) in [0,1,2,3]

    def is_project_accepted_member(self, project):
        return project.user_status(self) == 2


class AstakosUserAuthProviderManager(models.Manager):

    def active(self, **filters):
        return self.filter(active=True, **filters)


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
        return auth_providers.get_provider(self.module)

    @property
    def details_display(self):
        try:
          return self.settings.get_details_tpl_display % self.__dict__
        except:
          return ''

    @property
    def title_display(self):
        title_tpl = self.settings.get_title_display
        try:
            if self.settings.get_user_title_display:
                title_tpl = self.settings.get_user_title_display
        except Exception, e:
            pass
        try:
          return title_tpl % self.__dict__
        except:
          return self.settings.get_title_display % self.__dict__

    def can_remove(self):
        return self.user.can_remove_auth_provider(self.module)

    def delete(self, *args, **kwargs):
        ret = super(AstakosUserAuthProvider, self).delete(*args, **kwargs)
        if self.module == 'local':
            self.user.set_unusable_password()
            self.user.save()
        return ret

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
    limit = models.PositiveIntegerField(_('Limit'), null=True)    # obsolete field
    uplimit = models.BigIntegerField(_('Up limit'), null=True)
    resource = models.ForeignKey(Resource)
    user = models.ForeignKey(AstakosUser)

    class Meta:
        unique_together = ("resource", "user")


class ApprovalTerms(models.Model):
    """
    Model for approval terms
    """

    date = models.DateTimeField(
        _('Issue date'), db_index=True, default=datetime.now())
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
            msg = "User %d changed email from %s to %s" % (user.pk, old_email,
                                                          user.email)
            logger.log(LOGGING_LEVEL, msg)
            return user
        except EmailChange.DoesNotExist:
            raise ValueError(_('Invalid activation key.'))


class EmailChange(models.Model):
    new_email_address = models.EmailField(
        _(u'new e-mail address'),
        help_text=_('Your old email address will be used until you verify your new one.'))
    user = models.ForeignKey(
        AstakosUser, unique=True, related_name='emailchanges')
    requested_at = models.DateTimeField(default=datetime.now())
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
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    affiliation = models.CharField('Affiliation', max_length=255, blank=True)
    username = models.CharField(_('username'), max_length=30, unique=True, help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))
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

class SessionCatalog(models.Model):
    session_key = models.CharField(_('session key'), max_length=40)
    user = models.ForeignKey(AstakosUser, related_name='sessions', null=True)


### PROJECTS ###
################

def synced_model_metaclass(class_name, class_parents, class_attributes):

    new_attributes = {}
    sync_attributes = {}

    for name, value in class_attributes.iteritems():
        sync, underscore, rest = name.partition('_')
        if sync == 'sync' and underscore == '_':
            sync_attributes[rest] = value
        else:
            new_attributes[name] = value

    if 'prefix' not in sync_attributes:
        m = ("you did not specify a 'sync_prefix' attribute "
             "in class '%s'" % (class_name,))
        raise ValueError(m)

    prefix = sync_attributes.pop('prefix')
    class_name = sync_attributes.pop('classname', prefix + '_model')

    for name, value in sync_attributes.iteritems():
        newname = prefix + '_' + name
        if newname in new_attributes:
            m = ("class '%s' was specified with prefix '%s' "
                 "but it already has an attribute named '%s'"
                 % (class_name, prefix, newname))
            raise ValueError(m)

        new_attributes[newname] = value

    newclass = type(class_name, class_parents, new_attributes)
    return newclass


def make_synced(prefix='sync', name='SyncedState'):

    the_name = name
    the_prefix = prefix

    class SyncedState(models.Model):

        sync_classname      = the_name
        sync_prefix         = the_prefix
        __metaclass__       = synced_model_metaclass

        sync_new_state      = models.BigIntegerField(null=True)
        sync_synced_state   = models.BigIntegerField(null=True)
        STATUS_SYNCED       = 0
        STATUS_PENDING      = 1
        sync_status         = models.IntegerField(db_index=True)

        class Meta:
            abstract = True

        class NotSynced(Exception):
            pass

        def sync_init_state(self, state):
            self.sync_synced_state = state
            self.sync_new_state = state
            self.sync_status = self.STATUS_SYNCED

        def sync_get_status(self):
            return self.sync_status

        def sync_set_status(self):
            if self.sync_new_state != self.sync_synced_state:
                self.sync_status = self.STATUS_PENDING
            else:
                self.sync_status = self.STATUS_SYNCED

        def sync_set_synced(self):
            self.sync_synced_state = self.sync_new_state
            self.sync_status = self.STATUS_SYNCED

        def sync_get_synced_state(self):
            return self.sync_synced_state

        def sync_set_new_state(self, new_state):
            self.sync_new_state = new_state
            self.sync_set_status()

        def sync_get_new_state(self):
            return self.sync_new_state

        def sync_set_synced_state(self, synced_state):
            self.sync_synced_state = synced_state
            self.sync_set_status()

        def sync_get_pending_objects(self):
            kw = dict((the_prefix + '_status', self.STATUS_PENDING))
            return self.objects.filter(**kw)

        def sync_get_synced_objects(self):
            kw = dict((the_prefix + '_status', self.STATUS_SYNCED))
            return self.objects.filter(**kw)

        def sync_verify_get_synced_state(self):
            status = self.sync_get_status()
            state = self.sync_get_synced_state()
            verified = (status == self.STATUS_SYNCED)
            return state, verified

        def sync_is_synced(self):
            state, verified = self.sync_verify_get_synced_state()
            return verified

    return SyncedState

SyncedState = make_synced(prefix='sync', name='SyncedState')


class ProjectApplicationManager(ForUpdateManager):

    def user_projects(self, user):
        """
        Return projects accessed by specified user.
        """
        return self.filter(Q(owner=user) | Q(applicant=user) | \
                        Q(project__projectmembership__person=user)).order_by('pk').distinct()

    def search_by_name(self, *search_strings):
        q = Q()
        for s in search_strings:
            q = q | Q(name__icontains=s)
        return self.filter(q)


class ProjectApplication(models.Model):
    PENDING, APPROVED, REPLACED, UNKNOWN = 'Pending', 'Approved', 'Replaced', 'Unknown'
    applicant               =   models.ForeignKey(
                                    AstakosUser,
                                    related_name='projects_applied',
                                    db_index=True)

    state                   =   models.CharField(max_length=80,
                                                default=UNKNOWN)

    owner                   =   models.ForeignKey(
                                    AstakosUser,
                                    related_name='projects_owned',
                                    db_index=True)

    precursor_application   =   models.OneToOneField('ProjectApplication',
                                                     null=True,
                                                     blank=True,
                                                     db_index=True)

    name                    =   models.CharField(max_length=80)
    homepage                =   models.URLField(max_length=255, null=True)
    description             =   models.TextField(null=True, blank=True)
    start_date              =   models.DateTimeField()
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
    issue_date              =   models.DateTimeField()


    objects                 =   ProjectApplicationManager()

    def __unicode__(self):
        return "%s applied by %s" % (self.name, self.applicant)

    def add_resource_policy(self, service, resource, uplimit):
        """Raises ObjectDoesNotExist, IntegrityError"""
        q = self.projectresourcegrant_set
        resource = Resource.objects.get(service__name=service, name=resource)
        q.create(resource=resource, member_capacity=uplimit)

    def user_status(self, user):
        """
        100 OWNER
        0   REQUESTED
        1   PENDING
        2   ACCEPTED
        3   REMOVING
        4   REMOVED
       -1   User has no association with the project
        """
        if user == self.owner:
            status = 100
        else:
            try:
                membership = self.project.projectmembership_set.get(person=user)
                status = membership.state
            except Project.DoesNotExist:
                status = -1
            except ProjectMembership.DoesNotExist:
                status = -1

        return status

    def members_count(self):
        return self.project.approved_memberships.count()

    @property
    def grants(self):
        return self.projectresourcegrant_set.values('member_capacity', 'resource__name', 'resource__service__name')

    @property
    def resource_policies(self):
        return self.projectresourcegrant_set.all()

    @resource_policies.setter
    def resource_policies(self, policies):
        for p in policies:
            service = p.get('service', None)
            resource = p.get('resource', None)
            uplimit = p.get('uplimit', 0)
            self.add_resource_policy(service, resource, uplimit)

    @property
    def follower(self):
        try:
            return ProjectApplication.objects.get(precursor_application=self)
        except ProjectApplication.DoesNotExist:
            return

    def submit(self, resource_policies, applicant, comments,
               precursor_application=None):

        if precursor_application:
            self.precursor_application = precursor_application
            self.owner = precursor_application.owner
        else:
            self.owner = applicant

        self.id = None
        self.applicant = applicant
        self.comments = comments
        self.issue_date = datetime.now()
        self.state = self.PENDING
        self.save()
        self.resource_policies = resource_policies

    def _get_project(self):
        precursor = self
        while precursor:
            try:
                objects = Project.objects.select_for_update()
                project = objects.get(application=precursor)
                return project
            except Project.DoesNotExist:
                pass
            precursor = precursor.precursor_application

        return None

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
        if self.state != self.PENDING:
            m = _("cannot approve: project '%s' in state '%s'") % (
                    new_project_name, self.state)
            raise PermissionDenied(m) # invalid argument

        now = datetime.now()
        project = self._get_project()

        try:
            # needs SERIALIZABLE
            conflicting_project = Project.objects.get(name=new_project_name)
            if (conflicting_project.is_alive and
                conflicting_project != project):
                m = (_("cannot approve: project with name '%s' "
                       "already exists (serial: %s)") % (
                        new_project_name, conflicting_project.id))
                raise PermissionDenied(m) # invalid argument
        except Project.DoesNotExist:
            pass

        new_project = False
        if project is None:
            new_project = True
            project = Project(creation_date=now)

        project.name = new_project_name
        project.application = self
        project.last_approval_date = now
        project.save()

        if new_project:
            project.add_member(self.owner)

        # This will block while syncing,
        # but unblock before setting the membership state.
        # See ProjectMembership.set_sync()
        project.set_membership_pending_sync()

        precursor = self.precursor_application
        while precursor:
            precursor.state = self.REPLACED
            precursor.save()
            precursor = precursor.precursor_application

        self.state = self.APPROVED
        self.save()


class ProjectResourceGrant(models.Model):

    resource                =   models.ForeignKey(Resource)
    project_application     =   models.ForeignKey(ProjectApplication,
                                                  null=True)
    project_capacity        =   intDecimalField(default=QH_PRACTICALLY_INFINITE)
    project_import_limit    =   intDecimalField(default=QH_PRACTICALLY_INFINITE)
    project_export_limit    =   intDecimalField(default=QH_PRACTICALLY_INFINITE)
    member_capacity         =   intDecimalField(default=QH_PRACTICALLY_INFINITE)
    member_import_limit     =   intDecimalField(default=QH_PRACTICALLY_INFINITE)
    member_export_limit     =   intDecimalField(default=QH_PRACTICALLY_INFINITE)

    objects = ExtendedManager()

    class Meta:
        unique_together = ("resource", "project_application")


class Project(models.Model):

    application                 =   models.OneToOneField(
                                            ProjectApplication,
                                            related_name='project')
    last_approval_date          =   models.DateTimeField(null=True)

    members                     =   models.ManyToManyField(
                                            AstakosUser,
                                            through='ProjectMembership')

    deactivation_reason         =   models.CharField(max_length=255, null=True)
    deactivation_start_date     =   models.DateTimeField(null=True)
    deactivation_date           =   models.DateTimeField(null=True)

    creation_date               =   models.DateTimeField()
    name                        =   models.CharField(
                                            max_length=80,
                                            db_index=True,
                                            unique=True)

    TERMINATED  =   'TERMINATED'
    SUSPENDED   =   'SUSPENDED'

    objects     =   ForUpdateManager()

    def __str__(self):
        return _("<project %s '%s'>") % (self.id, self.application.name)

    __repr__ = __str__

    def is_deactivating(self):
        return bool(self.deactivation_start_date)

    def is_deactivated_synced(self):
        return bool(self.deactivation_date)

    def is_deactivated(self):
        return self.is_deactivated_synced() or self.is_deactivating()

    def is_still_approved(self):
        return bool(self.last_approval_date)

    def is_active(self):
        return not(self.is_deactivated())

    def is_inconsistent(self):
        now = datetime.now()
        dates = [self.creation_date,
                 self.last_approval_date,
                 self.deactivation_start_date,
                 self.deactivation_date]
        return any([date > now for date in dates])

    def set_deactivation_start_date(self):
        self.deactivation_start_date = datetime.now()

    def set_deactivation_date(self):
        self.deactivation_start_date = None
        self.deactivation_date = datetime.now()

    def violates_resource_grants(self):
        return False

    def violates_members_limit(self, adding=0):
        application = self.application
        return (len(self.approved_members) + adding >
                application.limit_on_members_number)

    @property
    def is_alive(self):
        return self.is_active()

    @property
    def approved_memberships(self):
        query = ProjectMembership.query_approved()
        return self.projectmembership_set.filter(query)

    @property
    def approved_members(self):
        return [m.person for m in self.approved_memberships]

    def set_membership_pending_sync(self):
        query = ProjectMembership.query_approved()
        sfu = self.projectmembership_set.select_for_update()
        members = sfu.filter(query)

        for member in members:
            member.state = member.PENDING
            member.save()

    def add_member(self, user):
        """
        Raises:
            django.exceptions.PermissionDenied
            astakos.im.models.AstakosUser.DoesNotExist
        """
        if isinstance(user, int):
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
        if isinstance(user, int):
            user = AstakosUser.objects.get(user=user)

        m = ProjectMembership.objects.get(person=user, project=self)
        m.remove()

    def terminate(self):
        self.set_deactivation_start_date()
        self.deactivation_reason = self.TERMINATED
        self.save()

    @property
    def is_terminated(self):
        return (self.is_deactivated() and
                self.deactivation_reason == self.TERMINATED)

    @property
    def is_suspended(self):
        return False

class ProjectMembership(models.Model):

    person              =   models.ForeignKey(AstakosUser)
    request_date        =   models.DateField(default=datetime.now())
    project             =   models.ForeignKey(Project)

    state               =   models.IntegerField(default=0)
    application         =   models.ForeignKey(
                                ProjectApplication,
                                null=True,
                                related_name='memberships')
    pending_application =   models.ForeignKey(
                                ProjectApplication,
                                null=True,
                                related_name='pending_memebrships')
    pending_serial      =   models.BigIntegerField(null=True, db_index=True)

    acceptance_date     =   models.DateField(null=True, db_index=True)
    leave_request_date  =   models.DateField(null=True)

    objects     =   ForUpdateManager()

    REQUESTED   =   0
    PENDING     =   1
    ACCEPTED    =   2
    REMOVING    =   3
    REMOVED     =   4
    INACTIVE    =   5

    APPROVED_SET    =   [PENDING, ACCEPTED, INACTIVE]

    @classmethod
    def query_approved(cls):
        return (Q(state=cls.PENDING) |
                Q(state=cls.ACCEPTED) |
                Q(state=cls.INACTIVE))

    class Meta:
        unique_together = ("person", "project")
        #index_together = [["project", "state"]]

    def __str__(self):
        return _("<'%s' membership in '%s'>") % (
                self.person.username, self.project)

    __repr__ = __str__

    def __init__(self, *args, **kwargs):
        self.state = self.REQUESTED
        super(ProjectMembership, self).__init__(*args, **kwargs)

    def _set_history_item(self, reason, date=None):
        if isinstance(reason, basestring):
            reason = ProjectMembershipHistory.reasons.get(reason, -1)

        history_item = ProjectMembershipHistory(
                            serial=self.id,
                            person=self.person.uuid,
                            project=self.project_id,
                            date=date or datetime.now(),
                            reason=reason)
        history_item.save()
        serial = history_item.id

    def accept(self):
        state = self.state
        if state != self.REQUESTED:
            m = _("%s: attempt to accept in state '%s'") % (self, state)
            raise AssertionError(m)

        now = datetime.now()
        self.acceptance_date = now
        self._set_history_item(reason='ACCEPT', date=now)
        self.state = (self.PENDING if self.project.is_active()
                      else self.INACTIVE)
        self.save()

    def remove(self):
        state = self.state
        if state not in [self.ACCEPTED, self.INACTIVE]:
            m = _("%s: attempt to remove in state '%s'") % (self, state)
            raise AssertionError(m)

        self._set_history_item(reason='REMOVE')
        self.state = self.REMOVING
        self.save()

    def reject(self):
        state = self.state
        if state != self.REQUESTED:
            m = _("%s: attempt to reject in state '%s'") % (self, state)
            raise AssertionError(m)

        # rejected requests don't need sync,
        # because they were never effected
        self._set_history_item(reason='REJECT')
        self.delete()

    def get_diff_quotas(self, sub_list=None, add_list=None, remove=False):
        if sub_list is None:
            sub_list = []

        if add_list is None:
            add_list = []

        sub_append = sub_list.append
        add_append = add_list.append
        holder = self.person.uuid

        synced_application = self.application
        if synced_application is not None:
            cur_grants = synced_application.projectresourcegrant_set.all()
            for grant in cur_grants:
                sub_append(QuotaLimits(
                               holder       = holder,
                               resource     = str(grant.resource),
                               capacity     = grant.member_capacity,
                               import_limit = grant.member_import_limit,
                               export_limit = grant.member_export_limit))

        if not remove:
            new_grants = self.pending_application.projectresourcegrant_set.all()
            for new_grant in new_grants:
                add_append(QuotaLimits(
                               holder       = holder,
                               resource     = str(new_grant.resource),
                               capacity     = new_grant.member_capacity,
                               import_limit = new_grant.member_import_limit,
                               export_limit = new_grant.member_export_limit))

        return (sub_list, add_list)

    def set_sync(self):
        state = self.state
        if state == self.PENDING:
            pending_application = self.pending_application
            if pending_application is None:
                m = _("%s: attempt to sync an empty pending application") % (
                    self,)
                raise AssertionError(m)
            self.application = pending_application
            self.pending_application = None
            self.pending_serial = None

            # project.application may have changed in the meantime,
            # in which case we stay PENDING;
            # we are safe to check due to select_for_update
            if self.application == self.project.application:
                self.state = self.ACCEPTED
            self.save()
        elif state == self.ACCEPTED:
            if self.pending_application:
                m = _("%s: attempt to sync in state '%s' "
                      "with a pending application") % (self, state)
                raise AssertionError(m)
            self.application = None
            self.pending_serial = None
            self.state = self.INACTIVE
            self.save()
        elif state == self.REMOVING:
            self.delete()
        else:
            m = _("%s: attempt to sync in state '%s'") % (self, state)
            raise AssertionError(m)

    def reset_sync(self):
        state = self.state
        if state in [self.PENDING, self.ACCEPTED, self.REMOVING]:
            self.pending_application = None
            self.pending_serial = None
            self.save()
        else:
            m = _("%s: attempt to reset sync in state '%s'") % (self, state)
            raise AssertionError(m)

class Serial(models.Model):
    serial  =   models.AutoField(primary_key=True)

def new_serial():
    s = Serial.objects.create()
    serial = s.serial
    s.delete()
    return serial

def sync_finish_serials(serials_to_ack=None):
    if serials_to_ack is None:
        serials_to_ack = qh_query_serials([])

    serials_to_ack = set(serials_to_ack)
    sfu = ProjectMembership.objects.select_for_update()
    memberships = list(sfu.filter(pending_serial__isnull=False))

    if memberships:
        for membership in memberships:
            serial = membership.pending_serial
            if serial in serials_to_ack:
                membership.set_sync()
            else:
                membership.reset_sync()

        transaction.commit()

    qh_ack_serials(list(serials_to_ack))
    return len(memberships)

def sync_all_projects():
    sync_finish_serials()

    PENDING = ProjectMembership.PENDING
    REMOVING = ProjectMembership.REMOVING
    objects = ProjectMembership.objects.select_for_update()

    sub_quota, add_quota = [], []

    serial = new_serial()

    pending = objects.filter(state=PENDING)
    for membership in pending:

        if membership.pending_application:
            m = "%s: impossible: pending_application is not None (%s)" % (
                membership, membership.pending_application)
            raise AssertionError(m)
        if membership.pending_serial:
            m = "%s: impossible: pending_serial is not None (%s)" % (
                membership, membership.pending_serial)
            raise AssertionError(m)

        membership.pending_application = membership.project.application
        membership.pending_serial = serial
        membership.get_diff_quotas(sub_quota, add_quota)
        membership.save()

    removing = objects.filter(state=REMOVING)
    for membership in removing:

        if membership.pending_application:
            m = ("%s: impossible: removing pending_application is not None (%s)"
                % (membership, membership.pending_application))
            raise AssertionError(m)
        if membership.pending_serial:
            m = "%s: impossible: pending_serial is not None (%s)" % (
                membership, membership.pending_serial)
            raise AssertionError(m)

        membership.pending_serial = serial
        membership.get_diff_quotas(sub_quota, add_quota, remove=True)
        membership.save()

    transaction.commit()
    # ProjectApplication.approve() unblocks here
    # and can set PENDING an already PENDING membership
    # which has been scheduled to sync with the old project.application
    # Need to check in ProjectMembership.set_sync()

    r = qh_add_quota(serial, sub_quota, add_quota)
    if r:
        m = "cannot sync serial: %d" % serial
        raise RuntimeError(m)

    sync_finish_serials([serial])

def sync_deactivating_projects():

    ACCEPTED = ProjectMembership.ACCEPTED
    PENDING = ProjectMembership.PENDING
    REMOVING = ProjectMembership.REMOVING

    psfu = Project.objects.select_for_update()
    projects = psfu.filter(deactivation_start_date__isnull=False)

    if not projects:
        return

    sub_quota, add_quota = [], []

    serial = new_serial()

    for project in projects:
        objects = project.projectmembership_set.select_for_update()
        memberships = objects.filter(Q(state=ACCEPTED) |
                                     Q(state=PENDING) | Q(state=REMOVING))
        for membership in memberships:
            if membership.state in (PENDING, REMOVING):
                m = "cannot sync deactivating project '%s'" % project
                raise RuntimeError(m)

            # state == ACCEPTED
            if membership.pending_application:
                m = "%s: impossible: pending_application is not None (%s)" % (
                    membership, membership.pending_application)
                raise AssertionError(m)
            if membership.pending_serial:
                m = "%s: impossible: pending_serial is not None (%s)" % (
                    membership, membership.pending_serial)
                raise AssertionError(m)

            membership.pending_serial = serial
            membership.get_diff_quotas(sub_quota, add_quota, remove=True)
            membership.save()

    transaction.commit()

    r = qh_add_quota(serial, sub_quota, add_quota)
    if r:
        m = "cannot sync serial: %d" % serial
        raise RuntimeError(m)

    sync_finish_serials([serial])

    # finalize deactivating projects
    deactivating_projects = psfu.filter(deactivation_start_date__isnull=False)
    for project in deactivating_projects:
        objects = project.projectmembership_set.select_for_update()
        memberships = list(objects.filter(Q(state=ACCEPTED) |
                                          Q(state=PENDING) | Q(state=REMOVING)))
        if not memberships:
            project.set_deactivation_date()
            project.save()

    transaction.commit()

def sync_projects():
    sync_all_projects()
    sync_deactivating_projects()

def trigger_sync(retries=3, retry_wait=1.0):
    transaction.commit()

    cursor = connection.cursor()
    locked = True
    try:
        while 1:
            cursor.execute("SELECT pg_try_advisory_lock(1)")
            r = cursor.fetchone()
            if r is None:
                m = "Impossible"
                raise AssertionError(m)
            locked = r[0]
            if locked:
                break

            retries -= 1
            if retries <= 0:
                return False
            sleep(retry_wait)

        sync_projects()
        return True

    finally:
        if locked:
            cursor.execute("SELECT pg_advisory_unlock(1)")
            cursor.fetchall()


class ProjectMembershipHistory(models.Model):
    reasons_list    =   ['ACCEPT', 'REJECT', 'REMOVE']
    reasons         =   dict((k, v) for v, k in enumerate(reasons_list))

    person  =   models.CharField(max_length=255)
    project =   models.BigIntegerField()
    date    =   models.DateField(default=datetime.now)
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


def fix_superusers(sender, **kwargs):
    # Associate superusers with AstakosUser
    admins = User.objects.filter(is_superuser=True)
    for u in admins:
        create_astakos_user(u)
post_syncdb.connect(fix_superusers)


def user_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    create_astakos_user(instance)
post_save.connect(user_post_save, sender=User)

def astakosuser_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    # TODO handle socket.error & IOError
    register_users((instance,))
post_save.connect(astakosuser_post_save, sender=AstakosUser)

def resource_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    register_resources((instance,))
post_save.connect(resource_post_save, sender=Resource)

def renew_token(sender, instance, **kwargs):
    if not instance.auth_token:
        instance.renew_token()
pre_save.connect(renew_token, sender=AstakosUser)
pre_save.connect(renew_token, sender=Service)


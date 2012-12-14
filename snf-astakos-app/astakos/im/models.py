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

from time import asctime
from datetime import datetime, timedelta
from base64 import b64encode
from urlparse import urlparse
from urllib import quote
from random import randint
from collections import defaultdict, namedtuple

from django.db import models, IntegrityError
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
    AUTH_TOKEN_DURATION, BILLING_FIELDS,
    EMAILCHANGE_ACTIVATION_DAYS, LOGGING_LEVEL,
    SITENAME, SERVICES, MODERATION_ENABLED)
from astakos.im import settings as astakos_settings
from astakos.im.endpoints.qh import (
    register_users, send_quota, register_resources, add_quota, QuotaLimits)
from astakos.im import auth_providers
#from astakos.im.endpoints.aquarium.producer import report_user_event
#from astakos.im.tasks import propagate_groupmembers_quota

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)

DEFAULT_CONTENT_TYPE = None
_content_type = None

PENDING, APPROVED, REPLACED, UNKNOWN = 'Pending', 'Approved', 'Replaced', 'Unknown'

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

    def renew_token(self):
        md5 = hashlib.md5()
        md5.update(self.name.encode('ascii', 'ignore'))
        md5.update(self.url.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        self.auth_token_expires = self.auth_token_created + \
            timedelta(hours=AUTH_TOKEN_DURATION)

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


class GroupKind(models.Model):
    name = models.CharField(_('Name'), max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.name


class AstakosGroup(Group):
    kind = models.ForeignKey(GroupKind)
    homepage = models.URLField(
        _('Homepage Url'), max_length=255, null=True, blank=True)
    desc = models.TextField(_('Description'), null=True)
    policy = models.ManyToManyField(
        Resource,
        null=True,
        blank=True,
        through='AstakosGroupQuota'
    )
    creation_date = models.DateTimeField(
        _('Creation date'),
        default=datetime.now()
    )
    issue_date = models.DateTimeField(
        _('Start date'),
        null=True
    )
    expiration_date = models.DateTimeField(
        _('Expiration date'),
        null=True
    )
    moderation_enabled = models.BooleanField(
        _('Moderated membership?'),
        default=True
    )
    approval_date = models.DateTimeField(
        _('Activation date'),
        null=True,
        blank=True
    )
    estimated_participants = models.PositiveIntegerField(
        _('Estimated #members'),
        null=True,
        blank=True,
    )
    max_participants = models.PositiveIntegerField(
        _('Maximum numder of participants'),
        null=True,
        blank=True
    )

    @property
    def is_disabled(self):
        if not self.approval_date:
            return True
        return False

    @property
    def is_enabled(self):
        if self.is_disabled:
            return False
        if not self.issue_date:
            return False
        if not self.expiration_date:
            return True
        now = datetime.now()
        if self.issue_date > now:
            return False
        if now >= self.expiration_date:
            return False
        return True

    def enable(self):
        if self.is_enabled:
            return
        self.approval_date = datetime.now()
        self.save()
        quota_disturbed.send(sender=self, users=self.approved_members)
        #propagate_groupmembers_quota.apply_async(
        #    args=[self], eta=self.issue_date)
        #propagate_groupmembers_quota.apply_async(
        #    args=[self], eta=self.expiration_date)

    def disable(self):
        if self.is_disabled:
            return
        self.approval_date = None
        self.save()
        quota_disturbed.send(sender=self, users=self.approved_members)

    def approve_member(self, person):
        m, created = self.membership_set.get_or_create(person=person)
        m.approve()

    @property
    def members(self):
        q = self.membership_set.select_related().all()
        return [m.person for m in q]

    @property
    def approved_members(self):
        q = self.membership_set.select_related().all()
        return [m.person for m in q if m.is_approved]

    @property
    def quota(self):
        d = defaultdict(int)
        for q in self.astakosgroupquota_set.select_related().all():
            d[q.resource] += q.uplimit or inf
        return d

    def add_policy(self, service, resource, uplimit, update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(service__name=service, name=resource)
        if update:
            AstakosGroupQuota.objects.update_or_create(
                group=self,
                resource=resource,
                defaults={'uplimit': uplimit}
            )
        else:
            q = self.astakosgroupquota_set
            q.create(resource=resource, uplimit=uplimit)

    @property
    def policies(self):
        return self.astakosgroupquota_set.select_related().all()

    @policies.setter
    def policies(self, policies):
        for p in policies:
            service = p.get('service', None)
            resource = p.get('resource', None)
            uplimit = p.get('uplimit', 0)
            update = p.get('update', True)
            self.add_policy(service, resource, uplimit, update)

    @property
    def owners(self):
        return self.owner.all()

    @property
    def owner_details(self):
        return self.owner.select_related().all()

    @owners.setter
    def owners(self, l):
        self.owner = l
        map(self.approve_member, l)

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

    astakos_groups = models.ManyToManyField(
        AstakosGroup, verbose_name=_('agroups'), blank=True,
        help_text=_(astakos_messages.ASTAKOSUSER_GROUPS_HELP),
        through='Membership')

    __has_signed_terms = False
    disturbed_quota = models.BooleanField(_('Needs quotaholder syncing'),
                                           default=False, db_index=True)

    objects = AstakosUserManager()

    owner = models.ManyToManyField(
        AstakosGroup, related_name='owner', null=True)

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
            if not p.is_active:
                continue
            grants = p.current_application.projectresourcegrant_set.all()
            for g in grants:
                d[str(g.resource)] += g.member_capacity or inf
        # TODO set default for remaining
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

    @property
    def extended_groups(self):
        return self.membership_set.select_related().all()

    @extended_groups.setter
    def extended_groups(self, groups):
        #TODO exceptions
        for name in (groups or ()):
            group = AstakosGroup.objects.get(name=name)
            self.membership_set.create(group=group)

    def save(self, update_timestamps=True, **kwargs):
        if update_timestamps:
            if not self.id:
                self.date_joined = datetime.now()
            self.updated = datetime.now()

        # update date_signed_terms if necessary
        if self.__has_signed_terms != self.has_signed_terms:
            self.date_signed_terms = datetime.now()

        if not self.id:
            # set username
            self.username = self.email

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
                is_active = %(is_active)s found.' % __self__
            raise ValidationError(m)

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
        if not provider_settings.is_available_for_login():
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

    def can_remove_auth_provider(self, provider):
        if len(self.get_active_auth_providers()) <= 1:
            return False
        return True

    def can_change_password(self):
        return self.has_auth_provider('local', auth_backend='astakos')

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

    def get_active_auth_providers(self):
        providers = []
        for provider in self.auth_providers.active():
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
                if MODERATION_ENABLED:
                    msg_extra = _(astakos_messages.ACCOUNT_PENDING_ACTIVATION_HELP)
                else:
                    url = self.get_resend_activation_url()
                    msg_extra = mark_safe(_(astakos_messages.ACCOUNT_PENDING_ACTIVATION_HELP) + \
                                u' ' + \
                                _('<a href="%s">%s?</a>') % (url,
                                _(astakos_messages.ACCOUNT_RESEND_ACTIVATION_PROMPT)))
        else:
            if MODERATION_ENABLED:
                message = _(astakos_messages.ACCOUNT_PENDING_MODERATION)
            else:
                message = astakos_messages.ACCOUNT_PENDING_ACTIVATION
                url = self.get_resend_activation_url()
                msg_extra = mark_safe(_('<a href="%s">%s?</a>') % (url,
                            _(astakos_messages.ACCOUNT_RESEND_ACTIVATION_PROMPT)))

        return mark_safe(message + u' '+ msg_extra)


class AstakosUserAuthProviderManager(models.Manager):

    def active(self):
        return self.filter(active=True)


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


class Membership(models.Model):
    person = models.ForeignKey(AstakosUser)
    group = models.ForeignKey(AstakosGroup)
    date_requested = models.DateField(default=datetime.now(), blank=True)
    date_joined = models.DateField(null=True, db_index=True, blank=True)

    class Meta:
        unique_together = ("person", "group")

    def save(self, *args, **kwargs):
        if not self.id:
            if not self.group.moderation_enabled:
                self.date_joined = datetime.now()
        super(Membership, self).save(*args, **kwargs)

    @property
    def is_approved(self):
        if self.date_joined:
            return True
        return False

    def approve(self):
        if self.is_approved:
            return
        if self.group.max_participants:
            assert len(self.group.approved_members) + 1 <= self.group.max_participants, \
            'Maximum participant number has been reached.'
        self.date_joined = datetime.now()
        self.save()
        quota_disturbed.send(sender=self, users=(self.person,))

    def disapprove(self):
        approved = self.is_approved()
        self.delete()
        if approved:
            quota_disturbed.send(sender=self, users=(self.person,))

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

class AstakosGroupQuota(models.Model):
    objects = ExtendedManager()
    limit = models.PositiveIntegerField(_('Limit'), null=True)    # obsolete field
    uplimit = models.BigIntegerField(_('Up limit'), null=True)
    resource = models.ForeignKey(Resource)
    group = models.ForeignKey(AstakosGroup, blank=True)

    class Meta:
        unique_together = ("resource", "group")

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
            user.email = email_change.new_email_address
            user.save()
            email_change.delete()
            return user
        except EmailChange.DoesNotExist:
            raise ValueError(_('Invalid activation key.'))


class EmailChange(models.Model):
    new_email_address = models.EmailField(
        _(u'new e-mail address'),
        help_text=_('Your old email address will be used until you verify your new one.'))
    user = models.ForeignKey(
        AstakosUser, unique=True, related_name='emailchange_user')
    requested_at = models.DateTimeField(default=datetime.now())
    activation_key = models.CharField(
        max_length=40, unique=True, db_index=True)

    objects = EmailChangeManager()

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

class MemberJoinPolicy(models.Model):
    policy = models.CharField(_('Policy'), max_length=255, unique=True, db_index=True)
    description = models.CharField(_('Description'), max_length=80)

    def __str__(self):
        return self.policy

class MemberLeavePolicy(models.Model):
    policy = models.CharField(_('Policy'), max_length=255, unique=True, db_index=True)
    description = models.CharField(_('Description'), max_length=80)

    def __str__(self):
        return self.policy

_auto_accept_join = False
def get_auto_accept_join():
    global _auto_accept_join
    if _auto_accept_join is not False:
        return _auto_accept_join
    try:
        auto_accept = MemberJoinPolicy.objects.get(policy='auto_accept')
    except:
        auto_accept = None
    _auto_accept_join = auto_accept
    return auto_accept

_closed_join = False
def get_closed_join():
    global _closed_join
    if _closed_join is not False:
        return _closed_join
    try:
        closed = MemberJoinPolicy.objects.get(policy='closed')
    except:
        closed = None
    _closed_join = closed
    return closed

_auto_accept_leave = False
def get_auto_accept_leave():
    global _auto_accept_leave
    if _auto_accept_leave is not False:
        return _auto_accept_leave
    try:
        auto_accept = MemberLeavePolicy.objects.get(policy='auto_accept')
    except:
        auto_accept = None
    _auto_accept_leave = auto_accept
    return auto_accept

_closed_leave = False
def get_closed_leave():
    global _closed_leave
    if _closed_leave is not False:
        return _closed_leave
    try:
        closed = MemberLeavePolicy.objects.get(policy='closed')
    except:
        closed = None
    _closed_leave = closed
    return closeds


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


class ProjectApplication(models.Model):

    applicant               =   models.ForeignKey(
                                    AstakosUser,
                                    related_name='my_project_applications',
                                    db_index=True
                                    )
    owner                   =   models.ForeignKey(
                                    AstakosUser,
                                    related_name='own_project_applications',
                                    db_index=True
                                    )
    precursor_application   =   models.OneToOneField('ProjectApplication',
                                                     null=True,
                                                     blank=True,
                                                     db_index=True
                                                     )
    state                   =   models.CharField(max_length=80,
                                                 default=UNKNOWN)

    name                    =   models.CharField(max_length=80)
    homepage                =   models.URLField(max_length=255, null=True,
                                                blank=True)
    description             =   models.TextField(null=True)
    start_date              =   models.DateTimeField()
    end_date                =   models.DateTimeField()
    member_join_policy      =   models.ForeignKey(MemberJoinPolicy)
    member_leave_policy     =   models.ForeignKey(MemberLeavePolicy)
    limit_on_members_number =   models.PositiveIntegerField(null=True,
                                                            blank=True)
    resource_grants         =   models.ManyToManyField(
                                    Resource,
                                    null=True,
                                    blank=True,
                                    through='ProjectResourceGrant'
                                    )
    comments                =   models.TextField(null=True, blank=True)
    issue_date              =   models.DateTimeField()

    states_list =   [PENDING, APPROVED, REPLACED, UNKNOWN]
    states      =   dict((k, v) for v, k in enumerate(states_list))

    def add_resource_policy(self, service, resource, uplimit, update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(service__name=service, name=resource)
        if update:
            ProjectResourceGrant.objects.update_or_create(
                project_application=self,
                resource=resource,
                defaults={'member_capacity': uplimit}
            )
        else:
            q = self.projectresourcegrant_set
            q.create(resource=resource, member_capacity=uplimit)

    @property
    def resource_policies(self):
        return self.projectresourcegrant_set.all()

    @resource_policies.setter
    def resource_policies(self, policies):
        for p in policies:
            service = p.get('service', None)
            resource = p.get('resource', None)
            uplimit = p.get('uplimit', 0)
            update = p.get('update', True)
            self.add_resource_policy(service, resource, uplimit, update)

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
        self.state = PENDING
        self.save()
        self.resource_policies = resource_policies

    def _get_project(self):
        precursor = self
        while precursor:
            try:
                project = precursor.project
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
        if self.state != PENDING:
            m = _("cannot approve: project '%s' in state '%s'") % (
                    new_project_name, self.state)
            raise PermissionDenied(m) # invalid argument

        now = datetime.now()
        project = self._get_project()
        if project is None:
            try:
                conflicting_project = Project.objects.get(name=new_project_name)
                if conflicting_project.is_alive:
                    m = _("cannot approve: project with name '%s' "
                          "already exists (serial: %s)") % (
                            new_project_name, conflicting_project.id)
                    raise PermissionDenied(m) # invalid argument
            except Project.DoesNotExist:
                pass
            project = Project(creation_date=now)

        project.latest_application = self
        project.set_membership_replaced()

        with exclusive_or_raise:
            project.status_set_flag(Project.SYNC_PENDING_DEFINITION)

        project.last_approval_date = now
        project.save()
        #ProjectMembership.add_to_project(self)
        project.add_member(self.owner)

        precursor = self.precursor_application
        while precursor:
            precursor.state = REPLACED
            precursor.save()
            precursor = precursor.precursor_application

        self.state = APPROVED
        self.save()

        transaction.commit()
        project.check_sync()

class ProjectResourceGrant(models.Model):

    resource                =   models.ForeignKey(Resource)
    project_application     =   models.ForeignKey(ProjectApplication,
                                                  blank=True)
    project_capacity        =   models.BigIntegerField(null=True)
    project_import_limit    =   models.BigIntegerField(null=True)
    project_export_limit    =   models.BigIntegerField(null=True)
    member_capacity         =   models.BigIntegerField(null=True)
    member_import_limit     =   models.BigIntegerField(null=True)
    member_export_limit     =   models.BigIntegerField(null=True)

    objects = ExtendedManager()

    class Meta:
        unique_together = ("resource", "project_application")


class Project(make_synced('app_sync'),
              make_synced('memb_sync'),
              models.Model):

    synced_application          =   models.OneToOneField(
                                            ProjectApplication,
                                            related_name='project',
                                            null=True)
    latest_application          =   models.OneToOneField(
                                            ProjectApplication,
                                            related_name='last_project')
    last_approval_date          =   models.DateTimeField(null=True)

    members                     =   models.ManyToManyField(
                                            AstakosUser,
                                            through='ProjectMembership')

    termination_start_date      =   models.DateTimeField(null=True)
    termination_date            =   models.DateTimeField(null=True)

    creation_date               =   models.DateTimeField()
    name                        =   models.CharField(
                                            max_length=80,
                                            db_index=True,
                                            unique=True)

    status                      =   models.IntegerField(db_index=True)

    SYNCHRONIZED                =   0
    SYNC_PENDING_MEMBERSHIP     =   (1 << 0)
    SYNC_PENDING_DEFINITION     =   (1 << 1)
    # SYNC_PENDING                =   (SYNC_PENDING_DEFINITION |
    #                                  SYNC_PENDING_MEMBERSHIP)


    def status_set_flag(self, s):
        self.status |= s

    def status_unset_flag(self, s):
        self.status &= ~s

    def status_is_set_flag(self, s):
        return self.status & s == s

    @property
    def current_application(self):
        return self.synced_application or self.latest_application

    @property
    def violated_resource_grants(self):
        if self.synced_application is None:
            return True
        # do something
        return False

    @property
    def violated_members_number_limit(self):
        application = self.synced_application
        if application is None:
            return True
        return len(self.approved_members) > application.limit_on_members_number

    @property
    def is_terminated(self):
        return bool(self.termination)

    @property
    def is_still_approved(self):
        return bool(self.last_approval_date)

    @property
    def is_active(self):
        if (self.is_terminated or
            not self.is_still_approved or
            self.violated_resource_grants):
            return False
#         if self.violated_members_number_limit:
#             return False
        return True
    
    @property
    def is_suspended(self):
        if (self.is_terminated or
            self.is_still_approved or
            not self.violated_resource_grants):
            return False
#             if not self.violated_members_number_limit:
#                 return False
        return True

    @property
    def is_alive(self):
        return self.is_active or self.is_suspended

    @property
    def is_inconsistent(self):
        now = datetime.now()
        if self.creation_date > now:
            return True
        if self.last_approval_date > now:
            return True
        if self.terminaton_date > now:
            return True
        return False

    @property
    def approved_memberships(self):
        return self.projectmembership_set.filter(
            synced_state=ProjectMembership.ACCEPTED)

    @property
    def approved_members(self):
        return [m.person for m in self.approved_memberships]

    def check_sync(self, hint=None):
        if self.status != self.SYNCHRONIZED:
            self.sync()

    def set_membership_replaced(self):
        members = [m for m in self.approved_memberships
                   if m.sync_is_synced()]

        for member in members:
            member.sync_set_new_state(member.REPLACED)
            member.save()

    def sync_membership(self):
        pending_members = self.projectmembership.filter(
            sync_status=ProjectMembership.STATUS_PENDING)
        for member in members:
            try:
                member.sync()
            except Exception:
                raise

        still_pending_members = self.members.filter(
            sync_status=ProjectMembership.STATUS_PENDING)
        if not still_pending_members:
            with exclusive_or_raise:
                self.status_unset_flag(self.SYNC_PENDING_MEMBERSHIP)
                self.save()

    def sync_definition(self):
        try:
            self.sync_membership()
        except Exception:
            raise
        else:
            with exclusive_or_raise:
                self.status_unset_flag(self.SYNC_PENDING_DEFINITION)
                self.synced_application = self.latest_application
                self.save()

    def sync(self):
        if self.status_is_set_flag(self.SYNC_PENDING_DEFINITION):
            self.sync_definition()
        if self.status_is_set_flag(self.SYNC_PENDING_MEMBERSHIP):
            self.sync_membership()

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
        self.termination_start_date = datetime.now()
        self.terminaton_date = None
        self.save()

        rejected = self.sync()
        if not rejected:
            self.termination_start_date = None
            self.termination_date = datetime.now()
            self.save()

#         try:
#             notification = build_notification(
#                 settings.SERVER_EMAIL,
#                 [self.current_application.owner.email],
#                 _(PROJECT_TERMINATION_SUBJECT) % self.__dict__,
#                 template='im/projects/project_termination_notification.txt',
#                 dictionary={'object':self.current_application}
#             ).send()
#         except NotificationError, e:
#             logger.error(e.messages)

    def suspend(self):
        self.last_approval_date = None
        self.save()
        self.sync()

#         try:
#             notification = build_notification(
#                 settings.SERVER_EMAIL,
#                 [self.current_application.owner.email],
#                 _(PROJECT_SUSPENSION_SUBJECT) % self.definition.__dict__,
#                 template='im/projects/project_suspension_notification.txt',
#                 dictionary={'object':self.current_application}
#             ).send()
#         except NotificationError, e:
#             logger.error(e.messages)



class ExclusiveOrRaise(object):
    """Context Manager to exclusively execute a critical code section.
       The exclusion must be global.
       (IPC semaphores will not protect across OS,
        DB locks will if it's the same DB)
    """

    class Busy(Exception):
        pass

    def __init__(self, locked=False):
        init = 0 if locked else 1
        from multiprocessing import Semaphore
        self._sema = Semaphore(init)

    def enter(self):
        acquired = self._sema.acquire(False)
        if not acquired:
            raise self.Busy()

    def leave(self):
        self._sema.release()

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.leave()


exclusive_or_raise = ExclusiveOrRaise(locked=False)


class ProjectMembership(SyncedState, models.Model):

    person              =   models.ForeignKey(AstakosUser)
    project             =   models.ForeignKey(Project)
    request_date        =   models.DateField(default=datetime.now())

    acceptance_date     =   models.DateField(null=True, db_index=True)
    leave_request_date  =   models.DateField(null=True)

    REQUESTED   =   0
    ACCEPTED    =   1
    REMOVED     =   2
    REJECTED    =   3   # never seen, because .delete()
    REPLACED    =   4   # when the project definition is replaced
                        # spontaneously goes back to ACCEPTED when synced

    class Meta:
        unique_together = ("person", "project")

    def __str__(self):
        return _("<'%s' membership in project '%s'>") % (
                self.person.username, self.project.application)

    __repr__ = __str__

    def __init__(self, *args, **kwargs):
        self.sync_init_state(self.REQUEST)
        super(ProjectMembership, self).__init__(*args, **kwargs)

    def _set_history_item(self, reason, date=None):
        if isinstance(reason, basestring):
            reason = ProjectMembershipHistory.reasons.get(reason, -1)

        history_item = ProjectMembershipHistory(
                            serial=self.id,
                            person=self.person,
                            project=self.project,
                            date=date,
                            reason=reason)
        history_item.save()
        serial = history_item.id

    def accept(self):
        state, verified = self.sync_verify_get_synced_state()
        if not verified:
            new_state = self.sync_get_new_state()
            m = _("%s: cannot accept: not synched (%s -> %s)") % (
                    self, state, new_state)
            raise self.NotSynced(m)

        if state != self.REQUESTED:
            m = _("%s: attempt to accept in state '%s'") % (self, state)
            raise AssertionError(m)

        now = datetime.now()
        self.acceptance_date = now
        self._set_history_item(reason='ACCEPT', date=now)
        self.sync_set_new_state(self.ACCEPTED)
        with exclusive_or_raise:
            self.project.status_set_flag(Project.SYNC_PENDING_MEMBERSHIP)
            self.project.save()
        self.save()

    def remove(self):
        state, verified = self.sync_verify_get_synced_state()
        if not verified:
            new_state = self.sync_get_new_state()
            m = _("%s: cannot remove: not synched (%s -> %s)") % (
                    self, state, new_state)
            raise self.NotSynced(m)

        if state != self.ACCEPTED:
            m = _("%s: attempt to remove in state '%s'") % (self, state)
            raise AssertionError(m)

        serial = self._set_history_item(reason='REMOVE')
        self.sync_set_new_state(self.REMOVED)
        with exclusive_or_raise:
            self.project.status_set_flag(Project.SYNC_PENDING_MEMBERSHIP)
            self.project.save()
        self.save()

    def reject(self):
        state, verified = self.sync_verify_get_synced_state()
        if not verified:
            new_state = self.sync_get_new_state()
            m = _("%s: cannot reject: not synched (%s -> %s)" % (
                    self, state, new_state))
            raise self.NotSynced(m)

        if state != self.REQUESTED:
            m = _("%s: attempt to remove in state '%s'") % (self, state)
            raise AssertionError(m)

        # rejected requests don't need sync,
        # because they were never effected
        self._set_history_item(reason='REJECT')
        self.delete()

    def get_quotas(self, limits_list=None, factor=1):
        if limits_list is None:
            limits_list = []
        append = limits_list.append
        holder = self.person.username
        all_grants = self.project.latest_application.resource_grants.all()
        for grant in all_grants:
            append(QuotaLimits(holder       = holder,
                               resource     = grant.resource.name,
                               capacity     = factor * grant.member_capacity,
                               import_limit = factor * grant.member_import_limit,
                               export_limit = factor * grant.member_export_limit))
        return limits_list

    def get_diff_quotas(self, limits_list=None, factor=1):
        if limits_list is None:
            limits_list = []

        append = limits_list.append
        holder = self.person.username

        synced_application = self.project.synced_application
        if synced_application is None:
            m = _("%s: attempt to read resource grants "
                  "of an uninitialized project") % (self,)
            raise AssertionException(m)

        # first, inverse all current limits, and index them by resource name
        cur_grants = synced_application.resource_grants.all()
        f = factor * -1
        tmp_grants = {}
        for grant in cur_grants:
            name = grant.resource.name
            tmp_grants[name] = QuotaLimits(
                            holder       = holder,
                            resource     = name,
                            capacity     = f * grant.member_capacity,
                            import_limit = f * grant.member_import_limit,
                            export_limit = f * grant.member_export_limit)

        # second, add each new limit to its inversed current
        new_grants = self.project.latest_application.resource_grants.all()
        for new_grant in new_grants:
            name = grant.resource.name
            cur_grant = tmp_grants.pop(name, None)
            if cur_grant is None:
                # if limits on a new resource, set 0 current values
                capacity = 0
                import_limit = 0
                export_limit = 0
            else:
                capacity = cur_grant.capacity
                import_limit = cur_grant.import_limit
                export_limit = cur_grant.export_limit

            capacity += new_grant.member_capacity
            import_limit += new_grant.member_import_limit
            export_limit += new_grant.member_export_limit

            append(QuotaLimits(holder       = holder,
                               resource     = name,
                               capacity     = capacity,
                               import_limit = import_limit,
                               export_limit = export_limit))

        # third, append all the inversed current limits for removed resources
        limits_list.extend(tmp_grants.itervalues())
        return limits_list

    def do_sync(self):
        state = self.sync_get_synced_state()
        new_state = self.sync_get_new_state()

        if state == self.REQUESTED and new_state == self.ACCEPTED:
            quotas = self.get_quotas(factor=1)
        elif state == self.ACCEPTED and new_state == self.REMOVED:
            quotas = self.get_quotas(factor=-1)
        elif state == self.ACCEPTED and new_state == self.REPLACED:
            quotas = self.get_diff_quotas(factor=1)
        else:
            m = _("%s: sync: called on invalid state ('%s' -> '%s')") % (
                    self, state, new_state)
            raise AssertionError(m)

        quotas = self.get_quotas(factor=factor)
        try:
            failure = add_quota(quotas)
            if failure:
                m = "%s: sync: add_quota failed" % (self,)
                raise RuntimeError(m)
        except Exception:
            raise
        else:
            self.sync_set_synced()

        # some states have instant side-effects/transitions
        if new_state == self.REMOVED:
            self.delete()
        elif new_state == self.REPLACED:
            self.sync_init_state(self.ACCEPTED)

    def sync(self):
        with exclusive_or_raise:
            self.do_sync()


class ProjectMembershipHistory(models.Model):
    reasons_list    =   ['ACCEPT', 'REJECT', 'REMOVE']
    reasons         =   dict((k, v) for v, k in enumerate(reasons_list))

    person  =   models.ForeignKey(AstakosUser)
    project =   models.ForeignKey(Project)
    date    =   models.DateField(default=datetime.now)
    reason  =   models.IntegerField()
    serial  =   models.BigIntegerField()


def filter_queryset_by_property(q, property):
    """
    Incorporate list comprehension for filtering querysets by property
    since Queryset.filter() operates on the database level.
    """
    return (p for p in q if getattr(p, property, False))

def get_alive_projects():
    return filter_queryset_by_property(
        Project.objects.all(),
        'is_alive'
    )

def get_active_projects():
    return filter_queryset_by_property(
        Project.objects.all(),
        'is_active'
    )

def _create_object(model, **kwargs):
    o = model.objects.create(**kwargs)
    o.save()
    return o


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


# def astakosuser_pre_save(sender, instance, **kwargs):
#     instance.aquarium_report = False
#     instance.new = False
#     try:
#         db_instance = AstakosUser.objects.get(id=instance.id)
#     except AstakosUser.DoesNotExist:
#         # create event
#         instance.aquarium_report = True
#         instance.new = True
#     else:
#         get = AstakosUser.__getattribute__
#         l = filter(lambda f: get(db_instance, f) != get(instance, f),
#                    BILLING_FIELDS)
#         instance.aquarium_report = True if l else False
# pre_save.connect(astakosuser_pre_save, sender=AstakosUser)

# def set_default_group(user):
#     try:
#         default = AstakosGroup.objects.get(name='default')
#         Membership(
#             group=default, person=user, date_joined=datetime.now()).save()
#     except AstakosGroup.DoesNotExist, e:
#         logger.exception(e)


def astakosuser_post_save(sender, instance, created, **kwargs):
#     if instance.aquarium_report:
#         report_user_event(instance, create=instance.new)
    if not created:
        return
#     set_default_group(instance)
    # TODO handle socket.error & IOError
    register_users((instance,))
post_save.connect(astakosuser_post_save, sender=AstakosUser)


def resource_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    register_resources((instance,))
post_save.connect(resource_post_save, sender=Resource)


# def on_quota_disturbed(sender, users, **kwargs):
# #     print '>>>', locals()
#     if not users:
#         return
#     send_quota(users)
#
# quota_disturbed = Signal(providing_args=["users"])
# quota_disturbed.connect(on_quota_disturbed)


# def send_quota_disturbed(sender, instance, **kwargs):
#     users = []
#     extend = users.extend
#     if sender == Membership:
#         if not instance.group.is_enabled:
#             return
#         extend([instance.person])
#     elif sender == AstakosUserQuota:
#         extend([instance.user])
#     elif sender == AstakosGroupQuota:
#         if not instance.group.is_enabled:
#             return
#         extend(instance.group.astakosuser_set.all())
#     elif sender == AstakosGroup:
#         if not instance.is_enabled:
#             return
#     quota_disturbed.send(sender=sender, users=users)
# post_delete.connect(send_quota_disturbed, sender=AstakosGroup)
# post_delete.connect(send_quota_disturbed, sender=Membership)
# post_save.connect(send_quota_disturbed, sender=AstakosUserQuota)
# post_delete.connect(send_quota_disturbed, sender=AstakosUserQuota)
# post_save.connect(send_quota_disturbed, sender=AstakosGroupQuota)
# post_delete.connect(send_quota_disturbed, sender=AstakosGroupQuota)


def renew_token(sender, instance, **kwargs):
    if not instance.auth_token:
        instance.renew_token()
pre_save.connect(renew_token, sender=AstakosUser)
pre_save.connect(renew_token, sender=Service)

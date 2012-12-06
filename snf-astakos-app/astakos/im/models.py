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

from time import asctime
from datetime import datetime, timedelta
from base64 import b64encode
from urlparse import urlparse
from urllib import quote
from random import randint
from collections import defaultdict

from django.db import models, IntegrityError
from django.contrib.auth.models import User, UserManager, Group, Permission
from django.utils.translation import ugettext as _
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models.signals import (
    pre_save, post_save, post_syncdb, post_delete
)
from django.contrib.contenttypes.models import ContentType

from django.dispatch import Signal
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.utils.http import int_to_base36
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.importlib import import_module
from django.core.validators import email_re

from astakos.im.settings import (
    DEFAULT_USER_LEVEL, INVITATIONS_PER_LEVEL,
    AUTH_TOKEN_DURATION, BILLING_FIELDS,
    EMAILCHANGE_ACTIVATION_DAYS, LOGGING_LEVEL
)
from astakos.im.endpoints.qh import (
    register_users, send_quota, register_resources
)
from astakos.im import auth_providers
from astakos.im.endpoints.aquarium.producer import report_user_event
from astakos.im.functions import send_invitation
#from astakos.im.tasks import propagate_groupmembers_quota

from astakos.im.notifications import build_notification

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)

DEFAULT_CONTENT_TYPE = None
try:
    content_type = ContentType.objects.get(app_label='im', model='astakosuser')
except:
    content_type = DEFAULT_CONTENT_TYPE

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
    name = models.CharField(_('Name'), max_length=255, unique=True, db_index=True)
    meta = models.ManyToManyField(ResourceMetadata)
    service = models.ForeignKey(Service)
    desc = models.TextField(_('Description'), null=True)
    unit = models.CharField(_('Name'), null=True, max_length=255)
    group = models.CharField(_('Group'), null=True, max_length=255)

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
    issue_date = models.DateTimeField('Start date', null=True)
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



class AstakosUserManager(UserManager):

    def get_auth_provider_user(self, provider, **kwargs):
        """
        Retrieve AstakosUser instance associated with the specified third party
        id.
        """
        kwargs = dict(map(lambda x: ('auth_providers__%s' % x[0], x[1]),
                          kwargs.iteritems()))
        return self.get(auth_providers__module=provider, **kwargs)

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

    class Meta:
        unique_together = ("provider", "third_party_identifier")

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
        p, created = Permission.objects.get_or_create(codename=pname,
                                                      name=pname.capitalize(),
                                                      content_type=content_type)
        self.user_permissions.add(p)

    def remove_permission(self, pname):
        if self.has_perm(pname):
            return
        p = Permission.objects.get(codename=pname,
                                   content_type=content_type)
        self.user_permissions.remove(p)

    @property
    def invitation(self):
        try:
            return Invitation.objects.get(username=self.email)
        except Invitation.DoesNotExist:
            return None

    def invite(self, email, realname):
        inv = Invitation(inviter=self, username=email, realname=realname)
        inv.save()
        send_invitation(inv)
        self.invitations = max(0, self.invitations - 1)
        self.save()

    @property
    def quota(self):
        """Returns a dict with the sum of quota limits per resource"""
        d = defaultdict(int)
        for q in self.policies:
            d[q.resource] += q.uplimit or inf
        for m in self.extended_groups:
            if not m.is_approved:
                continue
            g = m.group
            if not g.is_enabled:
                continue
            for r, uplimit in g.quota.iteritems():
                d[r] += uplimit or inf
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
        if self.is_active and self.activation_sent:
            # reset the activation sent
            self.activation_sent = None

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
        q = q.filter(is_active = self.is_active)
        if self.id:
            q = q.filter(~Q(id = self.id))
        if q.count() != 0:
            raise ValidationError({'__all__': [_(astakos_messages.UNIQUE_EMAIL_IS_ACTIVE_CONSTRAIN_ERR)]})

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
        if self.can_add_auth_provider(provider, **kwargs):
            self.auth_providers.create(module=provider, active=True, **kwargs)
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
                               identifier=pending.third_party_identifier)

        if email_re.match(pending.email or '') and pending.email != self.email:
            self.additionalmail_set.get_or_create(email=pending.email)

        pending.delete()
        return provider

    def remove_auth_provider(self, provider, **kwargs):
        self.auth_providers.get(module=provider, **kwargs).delete()

    # user urls
    def get_resend_activation_url(self):
        return reverse('send_activation', {'user_id': self.pk})

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

    objects = AstakosUserAuthProviderManager()

    class Meta:
        unique_together = (('identifier', 'module', 'user'), )

    @property
    def settings(self):
        return auth_providers.get_provider(self.module)

    @property
    def details_display(self):
        return self.settings.details_tpl % self.__dict__

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
                raise ValueError(_(astakos_messages.NEW_EMAIL_ADDR_RESERVED))
            # update user
            user = AstakosUser.objects.get(pk=email_change.user_id)
            user.email = email_change.new_email_address
            user.save()
            email_change.delete()
            return user
        except EmailChange.DoesNotExist:
            raise ValueError(_(astakos_messages.INVALID_ACTIVATION_KEY))


class EmailChange(models.Model):
    new_email_address = models.EmailField(_(u'new e-mail address'),
                                          help_text=_(astakos_messages.EMAIL_CHANGE_NEW_ADDR_HELP))
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

    class Meta:
        unique_together = ("provider", "third_party_identifier")

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

class MemberAcceptPolicy(models.Model):
    policy = models.CharField(_('Policy'), max_length=255, unique=True, db_index=True)
    description = models.CharField(_('Description'), max_length=80)

    def __str__(self):
        return self.policy

try:
    auto_accept = MemberAcceptPolicy.objects.get(policy='auto_accept')
except:
    auto_accept = None

class ProjectDefinition(models.Model):
    name = models.CharField(max_length=80)
    homepage = models.URLField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    member_accept_policy = models.ForeignKey(MemberAcceptPolicy)
    limit_on_members_number = models.PositiveIntegerField(null=True,blank=True)
    resource_grants = models.ManyToManyField(
        Resource,
        null=True,
        blank=True,
        through='ProjectResourceGrant'
    )
    
    def save(self):
        self.validate_name()
        super(ProjectDefinition, self).save()
    
    def validate_name(self):
        """
        Validate name uniqueness among all active projects.
        """
        alive_projects = list(get_alive_projects())
        q = filter(lambda p: p.definition.name==self.name, alive_projects)
        if q:
            raise ValidationError({'name': [_(astakos_messages.UNIQUE_PROJECT_NAME_CONSTRAIN_ERR)]})
    
    @property
    def violated_resource_grants(self):
        return False
    
    def add_resource_policy(self, service, resource, uplimit, update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        resource = Resource.objects.get(service__name=service, name=resource)
        if update:
            ProjectResourceGrant.objects.update_or_create(
                project_definition=self,
                resource=resource,
                defaults={'member_limit': uplimit}
            )
        else:
            q = self.projectresourcegrant_set
            q.create(resource=resource, member_limit=uplimit)

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
    
    def get_absolute_url(self):
        return reverse('project_application_detail', args=(self.serial,))


class ProjectResourceGrant(models.Model):
    objects = ExtendedManager()
    member_limit = models.BigIntegerField(null=True)
    project_limit = models.BigIntegerField(null=True)
    resource = models.ForeignKey(Resource)
    project_definition = models.ForeignKey(ProjectDefinition, blank=True)

    class Meta:
        unique_together = ("resource", "project_definition")

class ProjectApplication(models.Model):
    serial = models.CharField(
        primary_key=True,
        max_length=30,
        unique=True,
        default=uuid.uuid4().hex[:30]
    )
    applicant = models.ForeignKey(AstakosUser, related_name='my_project_applications')
    owner = models.ForeignKey(AstakosUser, related_name='own_project_applications')
    comments = models.TextField(null=True, blank=True)
    definition = models.OneToOneField(ProjectDefinition)
    issue_date = models.DateTimeField()
    precursor_application = models.OneToOneField('ProjectApplication',
        null=True,
        blank=True
    )

class Project(models.Model):
    serial = models.CharField(
        _('username'),
        primary_key=True,
        max_length=30,
        unique=True,
        default=uuid.uuid4().hex[:30]
    )
    application = models.OneToOneField(ProjectApplication, related_name='project')
    creation_date = models.DateTimeField()
    last_approval_date = models.DateTimeField()
    termination_date = models.DateTimeField()
    members = models.ManyToManyField(AstakosUser, through='ProjectMembership')
    last_synced_application = models.OneToOneField(
        ProjectApplication, related_name='last_project', null=True, blank=True
    )
    
    @property
    def definition(self):
        return self.application.definition
    
    @property
    def is_valid(self):
        try:
            self.application.definition.validate_name()
        except ValidationError:
            return False
        else:
            return True
    
    @property
    def is_active(self):
        if not self.is_valid:
            return False
        if not self.last_approval_date:
            return False
        if self.termination_date:
            return False
        if self.definition.violated_resource_grants:
            return False
        return True
    
    @property
    def is_terminated(self):
        if not self.is_valid:
            return False
        if not self.termination_date:
            return False
        return True
    
    @property
    def is_suspended(self):
        if not self.is_valid:
            return False
        if not self.termination_date:
            return False
        if not self.last_approval_date:
            if not self.definition.violated_resource_grants:
                return False
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
    def approved_members(self):
        return self.members.filter(is_accepted=True)
    
    def suspend(self):
        self.last_approval_date = None
        self.save()
    
    def terminate(self):
        self.terminaton_date = datetime.now()
        self.save()
    
    def sync(self):
        c, rejected = send_quota(self.approved_members)
        return rejected

class ProjectMembership(models.Model):
    person = models.ForeignKey(AstakosUser)
    project = models.ForeignKey(Project)
    issue_date = models.DateField(default=datetime.now())
    decision_date = models.DateField(null=True, db_index=True)
    is_accepted = models.BooleanField(
        _('Whether the membership application is accepted'),
        default=False
    )

    class Meta:
        unique_together = ("person", "project")

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

def _lookup_object(model, **kwargs):
    """
    Returns an object of the specific model matching the given lookup
    parameters.
    """
    if not kwargs:
        raise MissingIdentifier
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        raise ItemNotExists(model._meta.verbose_name, **kwargs)
    except model.MultipleObjectsReturned:
        raise MultipleItemsExist(model._meta.verbose_name, **kwargs)

def _create_object(model, **kwargs):
    o = model.objects.create(**kwargs)
    o.save()
    return o

def _update_object(model, id, save=True, **kwargs):
    o = self._lookup_object(model, id=id)
    if kwargs:
        o.__dict__.update(kwargs)
    if save:
        o.save()
    return o

def list_applications():
    return ProjectAppication.objects.all()

def submit_application(definition, applicant, comments, precursor_application=None, commit=True):
    if precursor_application:
        application = precursor_application.copy()
        application.precursor_application = precursor_application
    else:
        application = ProjectApplication(owner=applicant)
    application.definition = definition
    application.applicant = applicant
    application.comments = comments
    application.issue_date = datetime.now()
    if commit:
        definition.save()
        application.save()
        notification = build_notification(
        settings.SERVER_EMAIL,
        [settings.ADMINS],
        _(GROUP_CREATION_SUBJECT) % {'group':app.definition.name},
        _('An new project application identified by %(serial)s has been submitted.') % app.serial
    )
    notification.send()
    return application
    
def approve_application(serial):
    app = _lookup_object(ProjectAppication, serial=serial)
    notify = False
    if not app.precursor_application:
        kwargs = {
            'application':app,
            'creation_date':datetime.now(),
            'last_approval_date':datetime.now(),
        }
        project = _create_object(Project, **kwargs)
    else:
        project = app.precursor_application.project
        last_approval_date = project.last_approval_date
        if project.is_valid:
            project.application = app
            project.last_approval_date = datetime.now()
            project.save()
        else:
            raise Exception(_(astakos_messages.INVALID_PROJECT) % project.__dict__)
    
    rejected = synchonize_project(project.serial)
    if rejected:
        # revert to precursor
        project.appication = app.precursor_application
        if project.application:
            project.last_approval_date = last_approval_date
        project.save()
        rejected = synchonize_project(project.serial)
        if rejected:
            raise Exception(_(astakos_messages.QH_SYNC_ERROR))
    else:
        project.last_application_synced = app
        project.save()
        sender, recipients, subject, message
        notification = build_notification(
            settings.SERVER_EMAIL,
            [project.owner.email],
            _('Project application has been approved on %s alpha2 testing' % SITENAME),
            _('Your application request %(serial)s has been apporved.')
        )
        notification.send()


def list_projects(filter_property=None):
    if filter_property:
        return filter_queryset_by_property(
            Project.objects.all(),
            filter_property
        )
    return Project.objects.all()

def add_project_member(serial, user_id, request_user):
    project = _lookup_object(Project, serial=serial)
    user = _lookup_object(AstakosUser, id=user_id)
    if not project.owner == request_user:
        raise Exception(_(astakos_messages.NOT_PROJECT_OWNER))
    
    if not project.is_alive:
        raise Exception(_(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)
    if len(project.members) + 1 > project.limit_on_members_number:
        raise Exception(_(astakos_messages.MEMBER_NUMBER_LIMIT_REACHED))
    m = self._lookup_object(ProjectMembership, person=user, project=project)
    if m.is_accepted:
        return
    m.is_accepted = True
    m.decision_date = datetime.now()
    m.save()
    notification = build_notification(
        settings.SERVER_EMAIL,
        [user.email],
        _('Your membership on project %(name)s has been accepted.') % project.definition.__dict__, 
        _('Your membership on project %(name)s has been accepted.') % project.definition.__dict__,
    )
    notification.send()

def remove_project_member(serial, user_id, request_user):
    project = _lookup_object(Project, serial=serial)
    if not project.is_alive:
        raise Exception(_(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)
    if not project.owner == request_user:
        raise Exception(_(astakos_messages.NOT_PROJECT_OWNER))
    user = self.lookup_user(user_id)
    m = _lookup_object(ProjectMembership, person=user, project=project)
    if not m.is_accepted:
        return
    m.is_accepted = False
    m.decision_date = datetime.now()
    m.save()
    notification = build_notification(
        settings.SERVER_EMAIL,
        [user.email],
        _('Your membership on project %(name)s has been removed.') % project.definition.__dict__,
        _('Your membership on project %(name)s has been removed.') % project.definition.__dict__
    )
    notification.send()    

def suspend_project(serial):
    project = _lookup_object(Project, serial=serial)
    project.suspend()
    notification = build_notification(
        settings.SERVER_EMAIL,
        [project.owner.email],
        _('Project %(name)s has been suspended.') %  project.definition.__dict__,
        _('Project %(name)s has been suspended.') %  project.definition.__dict__
    )
    notification.send()

def terminate_project(serial):
    project = _lookup_object(Project, serial=serial)
    project.termination()
    notification = build_notification(
        settings.SERVER_EMAIL,
        [project.owner.email],
        _('Project %(name)s has been terminated.') %  project.definition.__dict__,
        _('Project %(name)s has been terminated.') %  project.definition.__dict__
    )
    notification.send()

def synchonize_project(serial):
    project = _lookup_object(Project, serial=serial)
    if project.app != project.last_application_synced:
        return project.sync()
     
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


def user_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    create_astakos_user(instance)


def set_default_group(user):
    try:
        default = AstakosGroup.objects.get(name='default')
        Membership(
            group=default, person=user, date_joined=datetime.now()).save()
    except AstakosGroup.DoesNotExist, e:
        logger.exception(e)


def astakosuser_pre_save(sender, instance, **kwargs):
    instance.aquarium_report = False
    instance.new = False
    try:
        db_instance = AstakosUser.objects.get(id=instance.id)
    except AstakosUser.DoesNotExist:
        # create event
        instance.aquarium_report = True
        instance.new = True
    else:
        get = AstakosUser.__getattribute__
        l = filter(lambda f: get(db_instance, f) != get(instance, f),
                   BILLING_FIELDS)
        instance.aquarium_report = True if l else False


def astakosuser_post_save(sender, instance, created, **kwargs):
    if instance.aquarium_report:
        report_user_event(instance, create=instance.new)
    if not created:
        return
    set_default_group(instance)
    # TODO handle socket.error & IOError
    register_users((instance,))


def resource_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    register_resources((instance,))


def send_quota_disturbed(sender, instance, **kwargs):
    users = []
    extend = users.extend
    if sender == Membership:
        if not instance.group.is_enabled:
            return
        extend([instance.person])
    elif sender == AstakosUserQuota:
        extend([instance.user])
    elif sender == AstakosGroupQuota:
        if not instance.group.is_enabled:
            return
        extend(instance.group.astakosuser_set.all())
    elif sender == AstakosGroup:
        if not instance.is_enabled:
            return
    quota_disturbed.send(sender=sender, users=users)


def on_quota_disturbed(sender, users, **kwargs):
#     print '>>>', locals()
    if not users:
        return
    send_quota(users)

def renew_token(sender, instance, **kwargs):
    if not instance.auth_token:
        instance.renew_token()

post_syncdb.connect(fix_superusers)
post_save.connect(user_post_save, sender=User)
pre_save.connect(astakosuser_pre_save, sender=AstakosUser)
post_save.connect(astakosuser_post_save, sender=AstakosUser)
post_save.connect(resource_post_save, sender=Resource)

quota_disturbed = Signal(providing_args=["users"])
quota_disturbed.connect(on_quota_disturbed)

post_delete.connect(send_quota_disturbed, sender=AstakosGroup)
post_delete.connect(send_quota_disturbed, sender=Membership)
post_save.connect(send_quota_disturbed, sender=AstakosUserQuota)
post_delete.connect(send_quota_disturbed, sender=AstakosUserQuota)
post_save.connect(send_quota_disturbed, sender=AstakosGroupQuota)
post_delete.connect(send_quota_disturbed, sender=AstakosGroupQuota)

pre_save.connect(renew_token, sender=AstakosUser)
pre_save.connect(renew_token, sender=Service)

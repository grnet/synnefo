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
from random import randint
from collections import defaultdict

from django.db import models, IntegrityError
from django.contrib.auth.models import User, UserManager, Group, Permission
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import (pre_save, post_save, post_syncdb,
                                      post_delete)
from django.contrib.contenttypes.models import ContentType

from django.dispatch import Signal
from django.db.models import Q

from astakos.im.settings import (DEFAULT_USER_LEVEL, INVITATIONS_PER_LEVEL,
                                 AUTH_TOKEN_DURATION, BILLING_FIELDS,
                                 EMAILCHANGE_ACTIVATION_DAYS, LOGGING_LEVEL)
from astakos.im.endpoints.quotaholder import (register_users, send_quota,
                                              register_resources)
from astakos.im.endpoints.aquarium.producer import report_user_event
from astakos.im.functions import send_invitation
from astakos.im.tasks import propagate_groupmembers_quota
from astakos.im.functions import send_invitation

logger = logging.getLogger(__name__)

DEFAULT_CONTENT_TYPE = None
try:
    content_type = ContentType.objects.get(app_label='im', model='astakosuser')
except:
    content_type = DEFAULT_CONTENT_TYPE

RESOURCE_SEPARATOR = '.'

class Service(models.Model):
    name = models.CharField('Name', max_length=255, unique=True, db_index=True)
    url = models.FilePathField()
    icon = models.FilePathField(blank=True)
    auth_token = models.CharField('Authentication Token', max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField('Token creation date', null=True)
    auth_token_expires = models.DateTimeField(
        'Token expiration date', null=True)

    def save(self, **kwargs):
        if not self.id:
            self.renew_token()
        super(Service, self).save(**kwargs)

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
    key = models.CharField('Name', max_length=255, unique=True, db_index=True)
    value = models.CharField('Value', max_length=255)


class Resource(models.Model):
    name = models.CharField('Name', max_length=255, unique=True, db_index=True)
    meta = models.ManyToManyField(ResourceMetadata)
    service = models.ForeignKey(Service)
    desc = models.TextField('Description', null=True)
    unit = models.CharField('Name', null=True, max_length=255)
    group = models.CharField('Group', null=True, max_length=255)

    def __str__(self):
        return '%s%s%s' % (self.service, RESOURCE_SEPARATOR, self.name)


class GroupKind(models.Model):
    name = models.CharField('Name', max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.name


class AstakosGroup(Group):
    kind = models.ForeignKey(GroupKind)
    homepage = models.URLField(
        'Homepage Url', max_length=255, null=True, blank=True)
    desc = models.TextField('Description', null=True)
    policy = models.ManyToManyField(
        Resource,
        null=True,
        blank=True,
        through='AstakosGroupQuota'
    )
    creation_date = models.DateTimeField(
        'Creation date',
        default=datetime.now()
    )
    issue_date = models.DateTimeField('Issue date', null=True)
    expiration_date = models.DateTimeField(
        'Expiration date',
         null=True
    )
    moderation_enabled = models.BooleanField(
        'Moderated membership?',
        default=True
    )
    approval_date = models.DateTimeField(
        'Activation date',
        null=True,
        blank=True
    )
    estimated_participants = models.PositiveIntegerField(
        'Estimated #members',
        null=True,
        blank=True,
    )
    max_participants = models.PositiveIntegerField(
        'Maximum numder of participants',
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
        propagate_groupmembers_quota.apply_async(
            args=[self], eta=self.issue_date)
        propagate_groupmembers_quota.apply_async(
            args=[self], eta=self.expiration_date)

    def disable(self):
        if self.is_disabled:
            return
        self.approval_date = None
        self.save()
        quota_disturbed.send(sender=self, users=self.approved_members)

    def approve_member(self, person):
        m, created = self.membership_set.get_or_create(person=person)
        # update date_joined in any case
        m.date_joined = datetime.now()
        m.save()

    def disapprove_member(self, person):
        self.membership_set.remove(person=person)

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
            d[q.resource] += q.uplimit
        return d
    
    def add_policy(self, service, resource, uplimit, update=True):
        """Raises ObjectDoesNotExist, IntegrityError"""
        print '#', locals()
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


class AstakosUser(User):
    """
    Extends ``django.contrib.auth.models.User`` by defining additional fields.
    """
    # Use UserManager to get the create_user method, etc.
    objects = UserManager()

    affiliation = models.CharField('Affiliation', max_length=255, blank=True)
    provider = models.CharField('Provider', max_length=255, blank=True)

    #for invitations
    user_level = DEFAULT_USER_LEVEL
    level = models.IntegerField('Inviter level', default=user_level)
    invitations = models.IntegerField(
        'Invitations left', default=INVITATIONS_PER_LEVEL.get(user_level, 0))

    auth_token = models.CharField('Authentication Token', max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField('Token creation date', null=True)
    auth_token_expires = models.DateTimeField(
        'Token expiration date', null=True)

    updated = models.DateTimeField('Update date')
    is_verified = models.BooleanField('Is verified?', default=False)

    # ex. screen_name for twitter, eppn for shibboleth
    third_party_identifier = models.CharField(
        'Third-party identifier', max_length=255, null=True, blank=True)

    email_verified = models.BooleanField('Email verified?', default=False)

    has_credits = models.BooleanField('Has credits?', default=False)
    has_signed_terms = models.BooleanField(
        'I agree with the terms', default=False)
    date_signed_terms = models.DateTimeField(
        'Signed terms date', null=True, blank=True)

    activation_sent = models.DateTimeField(
        'Activation sent data', null=True, blank=True)

    policy = models.ManyToManyField(
        Resource, null=True, through='AstakosUserQuota')

    astakos_groups = models.ManyToManyField(
        AstakosGroup, verbose_name=_('agroups'), blank=True,
        help_text=_("In addition to the permissions manually assigned, this user will also get all permissions granted to each group he/she is in."),
        through='Membership')

    __has_signed_terms = False
    disturbed_quota = models.BooleanField('Needs quotaholder syncing',
                                           default=False, db_index=True)

    owner = models.ManyToManyField(
        AstakosGroup, related_name='owner', null=True)

    class Meta:
        unique_together = ("provider", "third_party_identifier")

    def __init__(self, *args, **kwargs):
        super(AstakosUser, self).__init__(*args, **kwargs)
        self.__has_signed_terms = self.has_signed_terms
        if not self.id and not self.is_active:
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
            d[q.resource] += q.uplimit
        for m in self.extended_groups:
            if not m.is_approved:
                continue
            g = m.group
            if not g.is_enabled:
                continue
            for r, uplimit in g.quota.iteritems():
                d[r] += uplimit

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
        for name in groups:
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
            while not self.username:
                username = uuid.uuid4().hex[:30]
                try:
                    AstakosUser.objects.get(username=username)
                except AstakosUser.DoesNotExist:
                    self.username = username
            if not self.provider:
                self.provider = 'local'
        self.validate_unique_email_isactive()
        if self.is_active and self.activation_sent:
            # reset the activation sent
            self.activation_sent = None

        super(AstakosUser, self).save(**kwargs)

    def renew_token(self):
        md5 = hashlib.md5()
        md5.update(self.username)
        md5.update(self.realname.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        self.auth_token_expires = self.auth_token_created + \
            timedelta(hours=AUTH_TOKEN_DURATION)
        msg = 'Token renewed for %s' % self.email
        logger.log(LOGGING_LEVEL, msg)

    def __unicode__(self):
        return '%s (%s)' % (self.realname, self.email)

    def conflicting_email(self):
        q = AstakosUser.objects.exclude(username=self.username)
        q = q.filter(email=self.email)
        if q.count() != 0:
            return True
        return False

    def validate_unique_email_isactive(self):
        """
        Implements a unique_together constraint for email and is_active fields.
        """
        q = AstakosUser.objects.exclude(username=self.username)
        q = q.filter(email=self.email)
        q = q.filter(is_active=self.is_active)
        if q.count() != 0:
            raise ValidationError({'__all__': [_('Another account with the same email & is_active combination found.')]})

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

    def store_disturbed_quota(self, set=True):
        self.disturbed_qutoa = set
        self.save()


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
        self.date_joined = datetime.now()
        self.save()
        quota_disturbed.send(sender=self, users=(self.person,))

    def disapprove(self):
        self.delete()
        quota_disturbed.send(sender=self, users=(self.person,))

class AstakosQuotaManager(models.Manager):
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
    objects = AstakosQuotaManager()
    limit = models.PositiveIntegerField('Limit', null=True)    # obsolete field
    uplimit = models.BigIntegerField('Up limit', null=True)
    resource = models.ForeignKey(Resource)
    group = models.ForeignKey(AstakosGroup, blank=True)

    class Meta:
        unique_together = ("resource", "group")

class AstakosUserQuota(models.Model):
    objects = AstakosQuotaManager()
    limit = models.PositiveIntegerField('Limit', null=True)    # obsolete field
    uplimit = models.BigIntegerField('Up limit', null=True)
    resource = models.ForeignKey(Resource)
    user = models.ForeignKey(AstakosUser)

    class Meta:
        unique_together = ("resource", "user")


class ApprovalTerms(models.Model):
    """
    Model for approval terms
    """

    date = models.DateTimeField(
        'Issue date', db_index=True, default=datetime.now())
    location = models.CharField('Terms location', max_length=255)


class Invitation(models.Model):
    """
    Model for registring invitations
    """
    inviter = models.ForeignKey(AstakosUser, related_name='invitations_sent',
                                null=True)
    realname = models.CharField('Real name', max_length=255)
    username = models.CharField('Unique ID', max_length=255, unique=True)
    code = models.BigIntegerField('Invitation code', db_index=True)
    is_consumed = models.BooleanField('Consumed?', default=False)
    created = models.DateTimeField('Creation date', auto_now_add=True)
    consumed = models.DateTimeField('Consumption date', null=True, blank=True)

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
                AstakosUser.objects.get(email=email_change.new_email_address)
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
            raise ValueError(_('Invalid activation key'))


class EmailChange(models.Model):
    new_email_address = models.EmailField(_(u'new e-mail address'),
                                          help_text=_(u'Your old email address will be used until you verify your new one.'))
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


def create_astakos_user(u):
    try:
        AstakosUser.objects.get(user_ptr=u.pk)
    except AstakosUser.DoesNotExist:
        extended_user = AstakosUser(user_ptr_id=u.pk)
        extended_user.__dict__.update(u.__dict__)
        extended_user.renew_token()
        extended_user.save()
    except BaseException, e:
        logger.exception(e)
        pass


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
    instance.renew_token()


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
    print '>>>', locals()
    if not users:
        return
    send_quota(users)

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

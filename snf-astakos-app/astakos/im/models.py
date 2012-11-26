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
from random import randint

from django.db import models, IntegrityError
from django.contrib.auth.models import User, UserManager, Group
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save, post_syncdb
from django.db.models import Q
from django.conf import settings

from astakos.im.settings import DEFAULT_USER_LEVEL, INVITATIONS_PER_LEVEL, \
    AUTH_TOKEN_DURATION, BILLING_FIELDS, QUEUE_CONNECTION, SITENAME, \
    EMAILCHANGE_ACTIVATION_DAYS, LOGGING_LEVEL

QUEUE_CLIENT_ID = 3 # Astakos.

logger = logging.getLogger(__name__)

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
    invitations = models.IntegerField('Invitations left', default=INVITATIONS_PER_LEVEL.get(user_level, 0))

    auth_token = models.CharField('Authentication Token', max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField('Token creation date', null=True)
    auth_token_expires = models.DateTimeField('Token expiration date', null=True)

    updated = models.DateTimeField('Update date')
    is_verified = models.BooleanField('Is verified?', default=False)

    # ex. screen_name for twitter, eppn for shibboleth
    third_party_identifier = models.CharField('Third-party identifier', max_length=255, null=True, blank=True)

    email_verified = models.BooleanField('Email verified?', default=False)

    has_credits = models.BooleanField('Has credits?', default=False)
    has_signed_terms = models.BooleanField('Agree with the terms?', default=False)
    date_signed_terms = models.DateTimeField('Signed terms date', null=True, blank=True)
    
    activation_sent = models.DateTimeField('Activation sent data', null=True, blank=True)
    
    __has_signed_terms = False
    __groupnames = []
    
    class Meta:
        unique_together = ("provider", "third_party_identifier")
    
    def __init__(self, *args, **kwargs):
        super(AstakosUser, self).__init__(*args, **kwargs)
        self.__has_signed_terms = self.has_signed_terms
        if self.id:
            self.__groupnames = [g.name for g in self.groups.all()]
        else:
            self.is_active = False
    
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

    @property
    def invitation(self):
        try:
            return Invitation.objects.get(username=self.email)
        except Invitation.DoesNotExist:
            return None

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
                username =  uuid.uuid4().hex[:30]
                try:
                    AstakosUser.objects.get(username = username)
                except AstakosUser.DoesNotExist, e:
                    self.username = username
            if not self.provider:
                self.provider = 'local'
        report_user_event(self)
        self.validate_unique_email_isactive()
        if self.is_active and self.activation_sent:
            # reset the activation sent
            self.activation_sent = None
        super(AstakosUser, self).save(**kwargs)
        
        # set default group if does not exist
        groupname = 'default'
        if groupname not in self.__groupnames:
            try:
                group = Group.objects.get(name = groupname)
                self.groups.add(group)
            except Group.DoesNotExist, e:
                logger.exception(e)
    
    def renew_token(self):
        md5 = hashlib.md5()
        md5.update(settings.SECRET_KEY)
        md5.update(self.username)
        md5.update(self.realname.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        self.auth_token_expires = self.auth_token_created + \
                                  timedelta(hours=AUTH_TOKEN_DURATION)
        msg = 'Token renewed for %s' % self.email
        logger._log(LOGGING_LEVEL, msg, [])

    def __unicode__(self):
        return self.username
    
    def conflicting_email(self):
        q = AstakosUser.objects.exclude(username = self.username)
        q = q.filter(email = self.email)
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
            raise ValidationError({'__all__':[_('Another account with the same email & is_active combination found.')]})
    
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

class ApprovalTerms(models.Model):
    """
    Model for approval terms
    """

    date = models.DateTimeField('Issue date', db_index=True, default=datetime.now())
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

def report_user_event(user):
    def should_send(user):
        # report event incase of new user instance
        # or if specific fields are modified
        if not user.id:
            return True
        db_instance = AstakosUser.objects.get(id = user.id)
        for f in BILLING_FIELDS:
            if (db_instance.__getattribute__(f) != user.__getattribute__(f)):
                return True
        return False

    if QUEUE_CONNECTION and should_send(user):

        from astakos.im.queue.userevent import UserEvent
        from synnefo.lib.queue import exchange_connect, exchange_send, \
                exchange_close

        eventType = 'create' if not user.id else 'modify'
        body = UserEvent(QUEUE_CLIENT_ID, user, eventType, {}).format()
        conn = exchange_connect(QUEUE_CONNECTION)
        parts = urlparse(QUEUE_CONNECTION)
        exchange = parts.path[1:]
        routing_key = '%s.user' % exchange
        exchange_send(conn, routing_key, body)
        exchange_close(conn)

def _generate_invitation_code():
    while True:
        code = randint(1, 2L**63 - 1)
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
            email_change = self.model.objects.get(activation_key=activation_key)
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
    new_email_address = models.EmailField(_(u'new e-mail address'), help_text=_(u'Your old email address will be used until you verify your new one.'))
    user = models.ForeignKey(AstakosUser, unique=True, related_name='emailchange_user')
    requested_at = models.DateTimeField(default=datetime.now())
    activation_key = models.CharField(max_length=40, unique=True, db_index=True)

    objects = EmailChangeManager()

    def activation_key_expired(self):
        expiration_date = timedelta(days=EMAILCHANGE_ACTIVATION_DAYS)
        return self.requested_at + expiration_date < datetime.now()

class Service(models.Model):
    name = models.CharField('Name', max_length=255, unique=True)
    url = models.FilePathField()
    icon = models.FilePathField(blank=True)
    auth_token = models.CharField('Authentication Token', max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField('Token creation date', null=True)
    auth_token_expires = models.DateTimeField('Token expiration date', null=True)
    
    def save(self, **kwargs):
        if not self.id:
            self.renew_token()
        self.full_clean()
        super(Service, self).save(**kwargs)
    
    def renew_token(self):
        md5 = hashlib.md5()
        md5.update(settings.SECRET_KEY)
        md5.update(self.name.encode('ascii', 'ignore'))
        md5.update(self.url.encode('ascii', 'ignore'))
        md5.update(asctime())

        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        self.auth_token_expires = self.auth_token_created + \
                                  timedelta(hours=AUTH_TOKEN_DURATION)

class AdditionalMail(models.Model):
    """
    Model for registring invitations
    """
    owner = models.ForeignKey(AstakosUser)
    email = models.EmailField()

class PendingThirdPartyUser(models.Model):
    """
    Model for registring successful third party user authentications
    """
    third_party_identifier = models.CharField('Third-party identifier', max_length=255, null=True, blank=True)
    provider = models.CharField('Provider', max_length=255, blank=True)
    email = models.EmailField(_('e-mail address'), blank=True, null=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    affiliation = models.CharField('Affiliation', max_length=255, blank=True)
    username = models.CharField(_('username'), max_length=30, unique=True, help_text=_("Required. 30 characters or fewer. Letters, numbers and @/./+/-/_ characters"))
    
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

def create_astakos_user(u):
    try:
        AstakosUser.objects.get(user_ptr=u.pk)
    except AstakosUser.DoesNotExist:
        extended_user = AstakosUser(user_ptr_id=u.pk)
        extended_user.__dict__.update(u.__dict__)
        extended_user.renew_token()
        extended_user.save()
    except:
        pass

def superuser_post_syncdb(sender, **kwargs):
    # if there was created a superuser
    # associate it with an AstakosUser
    admins = User.objects.filter(is_superuser=True)
    for u in admins:
        create_astakos_user(u)

post_syncdb.connect(superuser_post_syncdb)

def superuser_post_save(sender, instance, **kwargs):
    if instance.is_superuser:
        create_astakos_user(instance)

post_save.connect(superuser_post_save, sender=User)
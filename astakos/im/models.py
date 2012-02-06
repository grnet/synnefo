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

from time import asctime
from datetime import datetime, timedelta
from base64 import b64encode

from django.db import models
from django.contrib.auth.models import User, UserManager

from astakos.im.interface import get_quota, set_quota
from astakos.im.settings import DEFAULT_USER_LEVEL, INVITATIONS_PER_LEVEL, AUTH_TOKEN_DURATION

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
    invitations = models.IntegerField('Invitations left', default=INVITATIONS_PER_LEVEL[user_level])
    
    auth_token = models.CharField('Authentication Token', max_length=32,
                                  null=True, blank=True)
    auth_token_created = models.DateTimeField('Token creation date', null=True)
    auth_token_expires = models.DateTimeField('Token expiration date', null=True)
    
    updated = models.DateTimeField('Update date')
    is_verified = models.BooleanField('Is verified?', default=False)
    
    # ex. screen_name for twitter, eppn for shibboleth
    third_party_identifier = models.CharField('Third-party identifier', max_length=255, null=True, blank=True)
    
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
    def quota(self):
        return get_quota(self.username)

    @quota.setter
    def quota(self, value):
        set_quota(self.username, value)
    
    @property
    def invitation(self):
        try:
            return Invitation.objects.get(username=self.email)
        except Invitation.DoesNotExist:
            return None
    
    def save(self, update_timestamps=True, **kwargs):
        if update_timestamps:
            if not self.id:
                # set username
                while not self.username:
                    username =  uuid.uuid4().hex[:30]
                    try:
                        AstakosUser.objects.get(username = username)
                    except AstakosUser.DoesNotExist, e:
                        self.username = username
                self.is_active = False
                if not self.provider:
                    self.provider = 'local'
                self.date_joined = datetime.now()
            self.updated = datetime.now()
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
    
    def __unicode__(self):
        return self.username

class Invitation(models.Model):
    """
    Model for registring invitations
    """
    inviter = models.ForeignKey(AstakosUser, related_name='invitations_sent',
                                null=True)
    realname = models.CharField('Real name', max_length=255)
    username = models.CharField('Unique ID', max_length=255)
    code = models.BigIntegerField('Invitation code', db_index=True)
    #obsolete: we keep it just for transfering the data
    is_accepted = models.BooleanField('Accepted?', default=False)
    is_consumed = models.BooleanField('Consumed?', default=False)
    created = models.DateTimeField('Creation date', auto_now_add=True)
    #obsolete: we keep it just for transfering the data
    accepted = models.DateTimeField('Acceptance date', null=True, blank=True)
    consumed = models.DateTimeField('Consumption date', null=True, blank=True)
    
    def consume(self):
        self.is_consumed = True
        self.consumed = datetime.now()
        self.save()
        
    def __unicode__(self):
        return '%s -> %s [%d]' % (self.inviter, self.username, self.code)

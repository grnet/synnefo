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

import logging
import hashlib

from time import asctime
from datetime import datetime, timedelta
from base64 import b64encode

from django.conf import settings
from django.db import models

from pithos.im.interface import get_quota, set_quota


class User(models.Model):
    ACCOUNT_STATE = (
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
        ('SUSPENDED', 'Suspended'),
        ('UNVERIFIED', 'Unverified'),
        ('PENDING', 'Pending')
    )
    
    uniq = models.CharField('Unique ID', max_length=255, null=True)
    
    realname = models.CharField('Real Name', max_length=255, default='')
    email = models.CharField('Email', max_length=255, default='')
    affiliation = models.CharField('Affiliation', max_length=255, default='')
    provider = models.CharField('Provider', max_length=255, default='')
    state = models.CharField('Account state', choices=ACCOUNT_STATE,
                                max_length=16, default='PENDING')
    
    #for invitations
    level = models.IntegerField('Inviter level', default=4)
    invitations = models.IntegerField('Invitations left', default=0)
    
    #for local
    password = models.CharField('Password', max_length=255, default='')
    
    is_admin = models.BooleanField('Admin?', default=False)
    
    auth_token = models.CharField('Authentication Token', max_length=32,
                                    null=True, blank=True)
    auth_token_created = models.DateTimeField('Token creation date',
                                                null=True)
    auth_token_expires = models.DateTimeField('Token expiration date',
                                                null=True)
    
    created = models.DateTimeField('Creation date')
    updated = models.DateTimeField('Update date')
    
    is_verified = models.BooleanField('Verified?', default=False)
    
    @property
    def quota(self):
        return get_quota(self.uniq)

    @quota.setter
    def quota(self, value):
        set_quota(self.uniq, value)
    
    @property
    def invitation(self):
        return Invitation.objects.get(uniq=self.uniq)
   
    def save(self, update_timestamps=True, **kwargs):
        if update_timestamps:
            if not self.id:
                self.created = datetime.now()
            self.updated = datetime.now()
        super(User, self).save(**kwargs)
    
    def renew_token(self):
        md5 = hashlib.md5()
        md5.update(self.uniq)
        md5.update(self.realname.encode('ascii', 'ignore'))
        md5.update(asctime())
        
        self.auth_token = b64encode(md5.digest())
        self.auth_token_created = datetime.now()
        self.auth_token_expires = self.auth_token_created + \
                                  timedelta(hours=settings.AUTH_TOKEN_DURATION)
    
    def __unicode__(self):
        return self.uniq

class Invitation(models.Model):
    inviter = models.ForeignKey(User, related_name='invitations_sent',
                                null=True)
    realname = models.CharField('Real name', max_length=255)
    uniq = models.CharField('Unique ID', max_length=255)
    code = models.BigIntegerField('Invitation code', db_index=True)
    is_consumed = models.BooleanField('Consumed?', default=False)
    created = models.DateTimeField('Creation date', auto_now_add=True)
    consumed = models.DateTimeField('Consumption date', null=True, blank=True)
    
    def __unicode__(self):
        return '%s -> %s [%d]' % (self.inviter, self.uniq, self.code)

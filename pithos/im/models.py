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

import datetime

from django.conf import settings
from django.db import models


class User(models.Model):
    
    ACCOUNT_STATE = (
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
        ('SUSPENDED', 'Suspended')
    )
    
    uniq = models.CharField('Unique ID', max_length=255, null=True)
    
    realname = models.CharField('Real Name', max_length=255, default='')
    email = models.CharField('Email', max_length=255, default='')
    affiliation = models.CharField('Affiliation', max_length=255, default='')
    state = models.CharField('Account state', choices=ACCOUNT_STATE, max_length=16, default='ACTIVE')
    
    # Lose these...
    quota = models.BigIntegerField('Storage Limit', default=settings.DEFAULT_QUOTA)
    max_invitations = models.IntegerField('Max number of invitations', null=True)
    
    is_admin = models.BooleanField('Admin', default=False)
    
    auth_token = models.CharField('Authentication Token', max_length=32, null=True)
    auth_token_created = models.DateTimeField('Time of auth token creation')
    auth_token_expires = models.DateTimeField('Time of auth token expiration')
    
    created = models.DateTimeField('Time of creation')
    updated = models.DateTimeField('Time of last update')
    
    def save(self, update_timestamps=True):
        if update_timestamps:
            if not self.id:
                self.created = datetime.datetime.now()
                self.auth_token_created = datetime.datetime.now()
                self.auth_token_expires = datetime.datetime.now()
            self.updated = datetime.datetime.now()
        super(User, self).save()
    
    class Meta:
        verbose_name = u'User'
    
    def __unicode__(self):
        return self.uniq

class Invitation(models.Model):
    source = models.ForeignKey(User, related_name="source")
    target = models.ForeignKey(User, related_name="target")
    accepted = models.BooleanField('Is the invitation accepted?', default=False)
    level = models.IntegerField('Invitation depth level', null=True)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = u'Invitation'

    def __unicode__(self):
        return "From: %s, To: %s" % (self.source, self.target)

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

import logging
import uuid

from datetime import tzinfo, timedelta
from django.conf import settings
from django.template import RequestContext
from django.contrib.sites.models import Site

from astakos.im.models import AstakosUser

class UTC(tzinfo):
   def utcoffset(self, dt):
       return timedelta(0)

   def tzname(self, dt):
       return 'UTC'

   def dst(self, dt):
       return timedelta(0)

def isoformat(d):
   """Return an ISO8601 date string that includes a timezone."""

   return d.replace(tzinfo=UTC()).isoformat()

def get_or_create_user(email, realname='', first_name='', last_name='', affiliation='', level=0, provider='local', password=''):
    """Find or register a user into the internal database
       and issue a token for subsequent requests.
    """
    user, created = AstakosUser.objects.get_or_create(email=email,
        defaults={
            'is_active': False,
            'password':password,
            'username':uuid.uuid4().hex[:30],
            'affiliation':affiliation,
            'level':level,
            'invitations':settings.INVITATIONS_PER_LEVEL[level],
            'provider':provider,
            'realname':realname,
            'first_name':first_name,
            'last_name':last_name
        })
    if created:
        user.renew_token()
        user.save()
        logging.info('Created user %s', user)
    
    return user

def get_context(request, extra_context={}, **kwargs):
    if not extra_context:
        extra_context = {}
    extra_context.update(kwargs)
    return RequestContext(request, extra_context)

def get_current_site(request, use_https=False):
    """
    returns the current site name and full domain (including prorocol)
    """
    protocol = use_https and 'https' or 'http'
    site = Site.objects.get_current()
    return site.name, '%s://%s' % (protocol, site.domain)
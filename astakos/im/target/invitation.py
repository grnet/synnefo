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

from datetime import datetime

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.contrib.auth import authenticate

from astakos.im.models import Invitation
from astakos.im.target.util import prepare_response
from astakos.im.util import get_or_create_user

def login(request):
    code = request.GET.get('code')
    try:
        invitation = Invitation.objects.get(code=code)
    except Invitation.DoesNotExist:
        return HttpResponseBadRequest('Wrong invitation code')
    
    if not invitation.is_accepted:
        invitation.is_accepted = True
        invitation.accepted = datetime.now()
        invitation.save()
        logging.info('Accepted invitation %s', invitation)
    
    user = get_or_create_user(username = uuid.uuid4().hex[:30],
                              realname = invitation.realname,
                              affiliation = 'Invitation',
                              level = invitation.inviter.level + 1,
                              email = invitation.uniq)
    
    # in order to login the user we must call authenticate first 
    authenticate(email=user.email, auth_token=user.auth_token)
    next = request.GET.get('next')
    
    return prepare_response(request, user, next, 'renew' in request.GET)

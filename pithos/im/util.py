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

import hashlib

from time import asctime
from datetime import datetime, timedelta
from base64 import b64encode

from django.conf import settings
from django.db import transaction

from models import User


@transaction.commit_on_success
def register_user(uniq, realname, affiliation):
    user = User()
    user.uniq = uniq
    user.realname = realname
    user.affiliation = affiliation
    user.save()
    create_auth_token(user)
    return user

@transaction.commit_on_success
def delete_user(user):
    if user is not None:
        user.delete()

@transaction.commit_on_success
def create_auth_token(user):
    md5 = hashlib.md5()
    md5.update(user.uniq)
    md5.update(user.realname.encode('ascii', 'ignore'))
    md5.update(asctime())
    
    user.auth_token = b64encode(md5.digest())
    user.auth_token_created = datetime.now()
    user.auth_token_expires = user.auth_token_created + \
                              timedelta(hours=settings.AUTH_TOKEN_DURATION)
    user.save()

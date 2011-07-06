# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

# Business Logic for working with users

from django.conf import settings

from synnefo.db.models import SynnefoUser
from django.db import transaction
import hashlib
import time
import string
from datetime import datetime, timedelta

@transaction.commit_on_success
def _register_user(f, u, unq, t):
    user = SynnefoUser()
    user.realname = f
    user.name = u
    user.uniq = unq
    user.type = t
    user.credit = 10 #TODO: Fix this when we have a per group policy
    user.save()
    create_auth_token(user)

def create_uname(fullname):
    fullname = fullname.strip()
    uname = None

    if fullname.find(' ') is not -1:
        (name, surname) = (fullname.split(' ')[0], string.join(fullname.split(' ')[-1:], ''))
        uname = "%s%s" % (string.join(surname[0:7],''), name[0])
        uname = uname.lower()
    else:
        uname = fullname[0:7].lower()

    return uname

@transaction.commit_on_success
def delete_user(user):
    if user is not None:
        user.delete()

def register_student(fullname, username, uniqid):
    _register_user(fullname, username, uniqid, 'STUDENT')

def register_professor(fullname, username, uniqid):
    _register_user(fullname, username, uniqid, 'PROFESSOR')

def register_user(fullname, email):
    uname = create_uname (fullname)
    _register_user(fullname, uname, email, 'USER')

@transaction.commit_on_success
def create_auth_token(user):
    md5 = hashlib.md5()
    md5.update(user.uniq)
    md5.update(user.name.encode('ascii', 'ignore'))
    md5.update(time.asctime())

    user.auth_token = md5.hexdigest()
    user.auth_token_created = datetime.now()
    user.auth_token_expires = user.auth_token_created + \
                              timedelta(hours=settings.AUTH_TOKEN_DURATION)
    user.save()

@transaction.commit_on_success
def create_tmp_token(user):
    md5 = hashlib.md5()
    md5.update(user.uniq)
    md5.update(user.name.encode('ascii', 'ignore'))
    md5.update(time.asctime())

    user.tmp_auth_token = md5.hexdigest()
    user.tmp_auth_token_expires = datetime.now() + \
                                  timedelta(minutes=settings.HELPDESK_TOKEN_DURATION_MIN)
    user.save()

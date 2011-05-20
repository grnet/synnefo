#
# Business Logic for working with users
#
# Copyright 2010 Greek Research and Technology Network
#
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

#def login(username, password):

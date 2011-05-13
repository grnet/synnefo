#
# Business Logic for working with users
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.db.models import SynnefoUser
from django.db import transaction
import hashlib
import time
from datetime import datetime

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
        (name, surname) = (fullname.split(' ')[0], fullname.split(' ')[-1:])
        uname = "%s%s" % (surname[0:7], name[0]).lower()
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
    md5.update(user.name)
    md5.update(time.asctime())

    user.auth_token = md5.hexdigest()
    user.auth_token_created = datetime.now()

    user.save()

#def login(username, password):

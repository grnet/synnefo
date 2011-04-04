#
# Business Logic for working with users
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.db.models import SynnefoUser
from django.db import transaction
import hashlib

@transaction.commit_on_success
def _register_user(f, u, unq, t):
    user = SynnefoUser()
    user.realname = f
    user.name = u
    user.uniq = unq
    user.type = t
    user.auth_token = create_auth_token(user)
    user.credit = 10 #TODO: Fix this when we have a per group policy
    user.save()

@transaction.commit_on_success
def delete_user(user):
    if user is not None:
        user.delete()

def register_student(fullname, username, uniqid):
    _register_user(fullname, username, uniqid, 'STUDENT')

def register_professor(fullname, username, uniqid):
    _register_user(fullname, username, uniqid, 'PROFESSOR')

def create_auth_token(user):
    md5 = hashlib.md5()
    md5.update(user.uniq)
    md5.update(user.name)
    return md5.hexdigest()



#def login(username, password):



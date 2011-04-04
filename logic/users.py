#
# Business Logic for working with users
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.db.models import SynnefoUser
from django.db import transaction
import hashlib

@transaction.commit_on_success
def _register_user(fullname, username, uniqid, type):
    user = SynnefoUser(fullname, username, uniqid, type)
    user.save()

def register_student(fullname, username, uniqid):
    _register_user(fullname, username, uniqid, 'STUDENT')

def register_professor(fullname, username, uniqid):
    _register_user(fullname, username, uniqid, 'PROFESSOR')

@transaction.commit_on_success
def delete_user(user):
    if user is not None:
        user.delete()

def create_auth_token(user):
    md5 = hashlib.md5
    md5.update(user.uniqid)
    md5.update(user.username)
    return md5.digest()

#def login(username, password):
    
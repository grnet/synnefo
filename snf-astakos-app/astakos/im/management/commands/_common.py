# Copyright 2012 GRNET S.A. All rights reserved.
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

from datetime import datetime

from django.utils.timesince import timesince, timeuntil
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from astakos.im.models import AstakosUser

content_type = None


def get_user(email_or_id, **kwargs):
    try:
        if email_or_id.isdigit():
            return AstakosUser.objects.get(id=int(email_or_id))
        else:
            return AstakosUser.objects.get(email=email_or_id, **kwargs)
    except AstakosUser.DoesNotExist, AstakosUser.MultipleObjectsReturned:
        return None


def format_bool(b):
    return 'YES' if b else 'NO'


def format_date(d):
    if not d:
        return ''

    if d < datetime.now():
        return timesince(d) + ' ago'
    else:
        return 'in ' + timeuntil(d)


def get_astakosuser_content_type():
    if content_type:
        return content_type

    try:
        return ContentType.objects.get(app_label='im',
                                       model='astakosuser')
    except:
        return content_type


def add_user_permission(user, pname):
    content_type = get_astakosuser_content_type()
    if user.has_perm(pname):
        return 0, None
    p, created = Permission.objects.get_or_create(codename=pname,
                                                  name=pname.capitalize(),
                                                  content_type=content_type)
    user.user_permissions.add(p)
    return 1, created


def add_group_permission(group, pname):
    content_type = get_astakosuser_content_type()
    if pname in [p.codename for p in group.permissions.all()]:
        return 0, None
    content_type = ContentType.objects.get(app_label='im',
                                           model='astakosuser')
    p, created = Permission.objects.get_or_create(codename=pname,
                                                  name=pname.capitalize(),
                                                  content_type=content_type)
    group.permissions.add(p)
    return 1, created


def remove_user_permission(user, pname):
    content_type = get_astakosuser_content_type()
    if user.has_perm(pname):
        return 0
    try:
        p = Permission.objects.get(codename=pname,
                                   content_type=content_type)
        user.user_permissions.remove(p)
        return 1
    except Permission.DoesNotExist:
        return -1


def remove_group_permission(group, pname):
    content_type = get_astakosuser_content_type()
    if pname not in [p.codename for p in group.permissions.all()]:
        return 0
    try:
        p = Permission.objects.get(codename=pname,
                                   content_type=content_type)
        group.permissions.remove(p)
        return 1
    except Permission.DoesNotExist:
        return -1

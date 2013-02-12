# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from synnefo.lib.ordereddict import OrderedDict
from astakos.im.models import AstakosUser

DEFAULT_CONTENT_TYPE = None


def get_user(email_or_id, **kwargs):
    try:
        if email_or_id.isdigit():
            return AstakosUser.objects.get(id=int(email_or_id))
        else:
            return AstakosUser.objects.get(email__iexact=email_or_id, **kwargs)
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

def format_dict(d, level=1, ident=22):
    iteritems = d.iteritems()
    if not isinstance(d, OrderedDict):
        iteritems = sorted(iteritems)

    l = ['%s: %s\n' % (k.rjust(level*ident), format(v, level+1))
         for k, v in iteritems]
    l.insert(0, '\n')
    return ''.join(l)

def format_set(s):
    return list(s)

def format(obj, level=1, ident=22):
    if isinstance(obj, bool):
        return format_bool(obj)
    elif isinstance(obj, datetime):
        return format_date(obj)
    elif isinstance(obj, dict):
        return format_dict(obj, level, ident)
    elif isinstance(obj, set):
        return format_set(obj)
    else:
        return obj

def get_astakosuser_content_type():
    try:
        return ContentType.objects.get(app_label='im',
                                       model='astakosuser')
    except:
        return DEFAULT_CONTENT_TYPE


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

def shortened(s, limit, suffix=True):
    length = len(s)
    if length <= limit:
        return s
    else:
        display = limit - 2
        if suffix:
            return '..' + s[-display:]
        else:
            return s[:display] + '..'

# Copyright 2012-2014 GRNET S.A. All rights reserved.
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

import uuid

from django.core.validators import validate_email
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from snf_django.management.commands import CommandError

from synnefo.util import units
from astakos.im.models import AstakosUser
from astakos.im import register
import sys


DEFAULT_CONTENT_TYPE = None


def read_from_file(f_name):
    if f_name == '-':
        return sys.stdin.read()
    else:
        try:
            with open(f_name) as file_desc:
                return file_desc.read()
        except IOError as e:
            raise CommandError(e)


def get_user(email_or_id, **kwargs):
    try:
        if email_or_id.isdigit():
            return AstakosUser.objects.get(id=int(email_or_id))
        else:
            return AstakosUser.objects.get(email__iexact=email_or_id, **kwargs)
    except (AstakosUser.DoesNotExist, AstakosUser.MultipleObjectsReturned):
        return None


def get_accepted_user(user_ident):
    if is_uuid(user_ident):
        try:
            user = AstakosUser.objects.get(uuid=user_ident)
        except AstakosUser.DoesNotExist:
            raise CommandError('There is no user with uuid: %s' %
                               user_ident)
    elif is_email(user_ident):
        try:
            user = AstakosUser.objects.get(username=user_ident)
        except AstakosUser.DoesNotExist:
            raise CommandError('There is no user with email: %s' %
                               user_ident)
    else:
        raise CommandError('Please specify user by uuid or email')

    if not user.is_accepted():
        raise CommandError('%s is not an accepted user.' % user.uuid)

    return user


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


def is_uuid(s):
    if s is None:
        return False
    try:
        uuid.UUID(s)
    except ValueError:
        return False
    else:
        return True


def is_email(s):
    if s is None:
        return False
    try:
        validate_email(s)
    except:
        return False
    else:
        return True


style_options = ', '.join(units.STYLES)


def check_style(style):
    if style not in units.STYLES:
        m = "Invalid unit style. Valid ones are %s." % style_options
        raise CommandError(m)


class ResourceDict(object):
    _object = None

    @classmethod
    def get(cls):
        if cls._object is None:
            rs = register.get_resources()
            cls._object = register.resources_to_dict(rs)
        return cls._object


def show_resource_value(number, resource, style):
    resources = ResourceDict.get()
    resource_dict = resources.get(resource)
    unit = resource_dict.get('unit') if resource_dict else None
    return units.show(number, unit, style)


def collect_holder_quotas(holder_quotas, style=None):
    print_data = []
    for source, source_quotas in holder_quotas.iteritems():
        for resource, values in source_quotas.iteritems():
            limit = show_resource_value(values['limit'], resource, style)
            usage = show_resource_value(values['usage'], resource, style)
            fields = (source, resource, limit, usage)
            print_data.append(fields)
    return print_data


def show_user_quotas(holder_quotas, style=None):
    labels = ('source', 'resource', 'limit', 'usage')
    print_data = collect_holder_quotas(holder_quotas, style=style)
    return print_data, labels


def show_quotas(qh_quotas, info=None, style=None):
    labels = ('holder', 'source', 'resource', 'limit', 'usage')
    if info is not None:
        labels = ('displayname',) + labels

    print_data = []
    for holder, holder_quotas in qh_quotas.iteritems():
        if info is not None:
            email = info.get(holder, "")

        h_data = collect_holder_quotas(holder_quotas, style=style)
        if info is not None:
            h_data = [(email, holder) + fields for fields in h_data]
        else:
            h_data = [(holder,) + fields for fields in h_data]
        print_data += h_data
    return print_data, labels

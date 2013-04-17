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

import os
import uuid
import string

from optparse import make_option
from collections import namedtuple

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from synnefo.lib.quotaholder.api import QH_PRACTICALLY_INFINITE

from astakos.im.models import AstakosUser, AstakosUserQuota, Resource

AddResourceArgs = namedtuple('AddQuotaArgs', ('resource',
                                              'capacity',
                                              ))

class Command(BaseCommand):
    help = """Import user quota limits from file or set quota
for a single user from the command line

    The file must contain non-empty lines, and each line must
    contain a single-space-separated list of values:

    <user> <resource name> <capacity>

    For example to grant the following user with 10 private networks
    (independent of any he receives from projects):

    6119a50b-cbc7-42c0-bafc-4b6570e3f6ac cyclades.network.private 10

    Similar syntax is used when setting quota from the command line:

    --set-capacity 6119a50b-cbc7-42c0-bafc-4b6570e3f6ac cyclades.vm 10

    The special value of 'default' sets the user setting to the default.
    """

    option_list = BaseCommand.option_list + (
        make_option('--from-file',
                    dest='from_file',
                    metavar='<exported-quotas.txt>',
                    help="Import quotas from file"),
        make_option('--set-capacity',
                    dest='set_capacity',
                    metavar='<uuid or email> <resource> <capacity>',
                    nargs=3,
                    help="Set capacity for a specified user/resource pair"),

        make_option('-f', '--no-confirm',
                    action='store_true',
                    default=False,
                    dest='force',
                    help="Do not ask for confirmation"),
    )

    def handle(self, *args, **options):
        from_file = options['from_file']
        set_capacity = options['set_capacity']
        force = options['force']

        if from_file is not None:
            if set_capacity is not None:
                raise CommandError("Cannot combine option `--from-file' with "
                                   "`--set-capacity'.")
            self.import_from_file(from_file)
            return

        if set_capacity is not None:
            user, resource, capacity = set_capacity
            self.set_limit(user, resource, capacity, force)
            return

        m = "Please use either `--from-file' or `--set-capacity' options"
        raise CommandError(m)

    def set_limit(self, user_ident, resource, capacity, force):
        if is_uuid(user_ident):
            try:
                user = AstakosUser.objects.get(uuid=user_ident)
            except AstakosUser.DoesNotExist:
                raise CommandError('Not found user having uuid: %s' %
                                   user_ident)
        elif is_email(user_ident):
            try:
                user = AstakosUser.objects.get(username=user_ident)
            except AstakosUser.DoesNotExist:
                raise CommandError('Not found user having email: %s' %
                                   user_ident)
        else:
            raise CommandError('Please specify user by uuid or email')

        if capacity != 'default':
            try:
                capacity = int(capacity)
            except ValueError:
                m = "Please specify capacity as a decimal integer or 'default'"
                raise CommandError(m)

        args = AddResourceArgs(resource=resource,
                               capacity=capacity,
                               )

        try:
            quota, default_capacity = user.get_resource_policy(resource)
        except Resource.DoesNotExist:
            raise CommandError("No such resource: %s" % resource)

        current = quota.capacity if quota is not None else 'default'

        if not force:
            self.stdout.write("user: %s (%s)\n" % (user.uuid, user.username))
            self.stdout.write("default capacity: %s\n" % default_capacity)
            self.stdout.write("current capacity: %s\n" % current)
            self.stdout.write("new capacity: %s\n" % capacity)
            self.stdout.write("Confirm? (y/n) ")
            response = raw_input()
            if string.lower(response) not in ['y', 'yes']:
                self.stdout.write("Aborted.\n")
                return

        if capacity == 'default':
            try:
                q = AstakosUserQuota.objects.get(
                        user=user,
                        resource__name=resource,
                        resource__name=name)
                q.delete()
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise CommandError("Failed to remove policy: %s" % e)
        else:
            try:
                user.add_resource_policy(*args)
            except Exception as e:
                raise CommandError("Failed to add policy: %s" % e)

    def import_from_file(self, location):
        try:
            f = open(location, 'r')
        except IOError, e:
            raise CommandError(e)

        for line in f.readlines():
            try:
                t = line.rstrip('\n').split(' ')
                user = t[0]
                args = AddResourceArgs(*t[1:])
            except(IndexError, TypeError):
                self.stdout.write('Invalid line format: %s:\n' % t)
                continue
            else:
                try:
                    user = AstakosUser.objects.get(uuid=user)
                except AstakosUser.DoesNotExist:
                    self.stdout.write('Not found user having uuid: %s\n' % user)
                    continue
                else:
                    try:
                        user.add_resource_policy(*args)
                    except Exception, e:
                        self.stdout.write('Failed to policy: %s\n' % e)
                        continue
            finally:
                f.close()


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

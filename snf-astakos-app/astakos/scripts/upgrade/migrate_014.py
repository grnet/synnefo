# Copyright 2013 GRNET S.A. All rights reserved.
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

from subprocess import call
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'
from astakos.im.models import UserSetting, AstakosUserQuota, Resource
from astakos.im.quotas import qh_sync_users

from optparse import OptionParser

parser = OptionParser()
parser.add_option("--usersetting", dest="usersetting",
                  action="store_true", default=False,
                  help="Only migrate user-specific settings",
                  )

SETTING = 'PENDING_APPLICATION_LIMIT'
RESOURCE = 'astakos.pending_app'


def migrate_user_setting():
    print 'Migrating user-specific settings...'
    try:
        resource = Resource.objects.get(name=RESOURCE)
    except Resource.DoesNotExist:
        print "Resource '%s' not found." % RESOURCE
        exit()

    users = set()
    settings = UserSetting.objects.filter(setting=SETTING)
    for setting in settings:
        user = setting.user
        value = setting.value
        q, created = AstakosUserQuota.objects.get_or_create(
            user=user, resource=resource,
            defaults={'capacity': value})
        if not created:
            print "Base quota already exists: %s %s" % (user.uuid, RESOURCE)
            continue
        print "Migrated base quota: %s %s %s" % (user.uuid, RESOURCE, value)
        users.add(user)

    qh_sync_users(users)


def modify_limit():
    command = ['snf-manage', 'resource-modify',
               RESOURCE, '--limit-interactive']
    print 'Running "%s"...' % ' '.join(command)
    r = call(command)

    if r != 0:
        print ('Setting resource limit failed. Have you registered '
               'service astakos?')
        print 'Aborting.'
        exit()


def reconcile():
    command = ['snf-manage', 'reconcile-resources-astakos', '--fix', '--force']
    print 'Running "%s"...' % ' '.join(command)
    r = call(command)


def main():
    (options, args) = parser.parse_args()
    usersetting = options.usersetting

    if not usersetting:
        modify_limit()
        print
    migrate_user_setting()
    if not usersetting:
        print
        reconcile()


if __name__ == '__main__':
    main()

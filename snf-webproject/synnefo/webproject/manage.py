# Copyright (C) 2010-2017 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import os
import errno
import grp
import pwd
from django.core.management import ManagementUtility
from django.core import management
from synnefo.util.version import get_component_version
from logging.config import dictConfig

# monkey patch to show synnefo version instead of django version
management.get_version = lambda: get_component_version('webproject')


class SynnefoManagementUtility(ManagementUtility):

    def main_help_text(self):
        return ManagementUtility.main_help_text(self, commands_only=True)


def configure_logging():
    try:
        from synnefo.settings import SNF_MANAGE_LOGGING_SETUP
        dictConfig(SNF_MANAGE_LOGGING_SETUP)
    except ImportError:
        import logging
        logging.basicConfig()
        log = logging.getLogger()
        log.warning("SNF_MANAGE_LOGGING_SETUP setting missing.")


def get_uid(user):
    if isinstance(user, int):
        return user
    elif user.isdigit():
        return int(user)
    else:
        try:
            return pwd.getpwnam(user).pw_uid
        except KeyError:
            raise Exception("No such user: '%s'" % user)


def get_gid(group):
    if isinstance(group, int):
        return group
    elif group.isdigit():
        return int(group)
    else:
        try:
            return grp.getgrnam(group).gr_gid
        except KeyError:
            raise Exception("No such group: '%s'" % group)


def set_uid_gid(uid, gid):
    if gid:
        os.setgid(gid)

    if uid:
        username = None
        try:
            username = pwd.getpwuid(uid)[0]
        except KeyError:
            pass

        # also set supplementary groups for the user
        if username is not None:
            if not gid:
                gid = os.getgid()

            try:
                os.initgroups(username, gid)
            except OSError, e:
                if e.errno != errno.EPERM:
                    raise

        os.setuid(uid)


def set_user_group():
    from synnefo import settings
    snf_user = getattr(settings, "SNF_MANAGE_USER", None)
    snf_group = getattr(settings, "SNF_MANAGE_GROUP", None)

    if snf_user is None:
        raise Exception("`SNF_MANAGE_USER` setting not defined")
    if snf_group is None:
        raise Exception("`SNF_MANAGE_GROUP` setting not defined")

    snf_uid = get_uid(snf_user)
    snf_gid = get_gid(snf_group)

    cur_uid = os.geteuid()
    cur_gid = os.getegid()

    if cur_uid != 0 and (cur_uid != snf_uid or cur_gid != snf_gid):
        sys.stderr.write("snf-manage must be run as user root or as "
                         "`SNF_USER`:SNF_GROUP (%s:%s)\n" % (str(snf_user),
                                                             str(snf_group)))

    if cur_uid == snf_uid:
        return

    set_uid_gid(snf_uid, snf_gid)


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = \
        os.environ.get('DJANGO_SETTINGS_MODULE', 'synnefo.settings')
    set_user_group()
    configure_logging()
    mu = SynnefoManagementUtility(sys.argv)
    mu.execute()


if __name__ == "__main__":
    main()

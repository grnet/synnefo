# Copyright (C) 2010-2014 GRNET S.A.
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

from optparse import make_option

from django.db.models import Q
from snf_django.management.commands import SynnefoCommand, CommandError
from astakos.im import transaction
from synnefo.util import units
from astakos.im import functions
from astakos.im import models
import astakos.api.projects as api
import synnefo.util.date as date_util
from snf_django.management import utils
from astakos.im.management.commands import _common


def make_policies(limits):
    policies = {}
    for (name, member_capacity, project_capacity) in limits:
        try:
            member_capacity = units.parse(member_capacity)
            project_capacity = units.parse(project_capacity)
        except units.ParseError:
            m = "Please specify capacity as a decimal integer"
            raise CommandError(m)
        policies[name] = {"member_capacity": member_capacity,
                          "project_capacity": project_capacity}
    return policies

Simple = type('Simple', (), {})


class Param(object):
    def __init__(self, key=Simple, mod=Simple, action=Simple, nargs=Simple,
                 is_main=False, help=""):
        self.key = key
        self.mod = mod
        self.action = action
        self.nargs = nargs
        self.is_main = is_main
        self.help = help


PARAMS = {
    "name": Param(key="realname", help="Set project name"),
    "owner": Param(mod=_common.get_accepted_user, help="Set project owner"),
    "homepage": Param(help="Set project homepage"),
    "description": Param(help="Set project description"),
    "end_date": Param(mod=date_util.isoparse, is_main=True,
                      help=("Set project end date in ISO format "
                            "(e.g. 2014-01-01T00:00Z)")),
    "join_policy": Param(key="member_join_policy", is_main=True,
                         mod=(lambda x: api.MEMBERSHIP_POLICY[x]),
                         help="Set join policy (auto, moderated, or closed)"),
    "leave_policy": Param(key="member_leave_policy", is_main=True,
                          mod=(lambda x: api.MEMBERSHIP_POLICY[x]),
                          help=("Set leave policy "
                                "(auto, moderated, or closed)")),
    "max_members": Param(key="limit_on_members_number", mod=int, is_main=True,
                         help="Set maximum members limit"),
    "private": Param(mod=utils.parse_bool, is_main=True,
                     help="Set project private"),
    "limit": Param(key="resources", mod=make_policies, is_main=True,
                   nargs=3, action="append",
                   help=("Set resource limits: "
                         "resource_name member_capacity project_capacity")),
}


def make_options():
    options = []
    for key, param in PARAMS.iteritems():
        opt = "--" + key.replace('_', '-')
        kwargs = {}
        if param.action is not Simple:
            kwargs["action"] = param.action
        if param.nargs is not Simple:
            kwargs["nargs"] = param.nargs
        kwargs["help"] = param.help
        options.append(make_option(opt, **kwargs))
    return tuple(options)


class Command(SynnefoCommand):
    args = "<project id> (or --all-system-projects)"
    help = "Modify an already initialized project"
    option_list = SynnefoCommand.option_list + make_options() + (
        make_option('--all-system-projects',
                    action='store_true',
                    default=False,
                    help="Modify in bulk all initialized system projects"),
        make_option('--exclude',
                    help=("If `--all-system-projects' is given, exclude projects"
                          " given as a list of uuids: uuid1,uuid2,uuid3")),
        )

    def check_args(self, args, all_base, exclude):
        if all_base and args or not all_base and len(args) != 1:
            m = "Please provide a project ID or --all-system-projects"
            raise CommandError(m)
        if not all_base and exclude:
            m = ("Option --exclude is meaningful only combined with "
                 " --all-system-projects.")
            raise CommandError(m)

    def mk_all_base_filter(self, all_base, exclude):
        flt = Q(state__in=models.Project.INITIALIZED_STATES, is_base=True)
        if exclude:
            exclude = exclude.split(',')
            flt &= ~Q(uuid__in=exclude)
        return flt

    @transaction.commit_on_success
    def handle(self, *args, **options):
        all_base = options["all_system_projects"]
        exclude = options["exclude"]
        self.check_args(args, all_base, exclude)

        try:
            changes = {}
            for key, value in options.iteritems():
                param = PARAMS.get(key)
                if param is None or value is None:
                    continue
                if all_base and not param.is_main:
                    m = "Cannot modify field '%s' in bulk" % key
                    raise CommandError(m)
                k = key if param.key is Simple else param.key
                v = value if param.mod is Simple else param.mod(value)
                changes[k] = v

            if all_base:
                flt = self.mk_all_base_filter(all_base, exclude)
                functions.modify_projects_in_bulk(flt, changes)
            else:
                functions.modify_project(args[0], changes)
        except BaseException as e:
            raise CommandError(e)

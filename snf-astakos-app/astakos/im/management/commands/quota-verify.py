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
from astakos.im import transaction

from astakos.im.models import Project
from astakos.im import quotas
from snf_django.management.utils import pprint_table
from snf_django.management.commands import SynnefoCommand

import logging
logger = logging.getLogger(__name__)


def differences(local_quotas, qh_quotas):
    unsynced = []
    unexpected = []
    for holder, h_quotas in local_quotas.iteritems():
        qh_h_quotas = qh_quotas.pop(holder, {})
        for source, s_quotas in h_quotas.iteritems():
            qh_s_quotas = qh_h_quotas.pop(source, {})
            for resource, value in s_quotas.iteritems():
                qh_value = qh_s_quotas.pop(resource, None)
                if value != qh_value:
                    data = (holder, source, resource, value, qh_value)
                    unsynced.append(data)
            unexpected += unexpected_resources(holder, source, qh_s_quotas)
        unexpected += unexpected_sources(holder, qh_h_quotas)
    unexpected += unexpected_holders(qh_quotas)
    return unsynced, unexpected


def unexpected_holders(qh_quotas):
    unexpected = []
    for holder, qh_h_quotas in qh_quotas.iteritems():
        unexpected += unexpected_sources(holder, qh_h_quotas)
    return unexpected


def unexpected_sources(holder, qh_h_quotas):
    unexpected = []
    for source, qh_s_quotas in qh_h_quotas.iteritems():
        unexpected += unexpected_resources(holder, source, qh_s_quotas)
    return unexpected


def unexpected_resources(holder, source, qh_s_quotas):
    unexpected = []
    for resource, qh_value in qh_s_quotas.iteritems():
        data = (holder, source, resource, None, qh_value)
        unexpected.append(data)
    return unexpected


class Command(SynnefoCommand):
    help = "Check the integrity of user and project quota"

    option_list = SynnefoCommand.option_list + (
        make_option("--include-unexpected-holdings",
                    default=False,
                    action="store_true",
                    help=("Also check for holdings that do not correspond "
                          "to Astakos projects or user. Note that fixing such "
                          "inconsistencies will permanently delete these "
                          "holdings.")),
        make_option("--fix", dest="fix",
                    default=False,
                    action="store_true",
                    help="Synchronize Quotaholder with Astakos DB."),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        write = self.stderr.write
        fix = options['fix']
        check_unexpected = options["include_unexpected_holdings"]

        projects = Project.objects.all()
        local_proj_quotas, local_user_quotas = \
            quotas.astakos_project_quotas(projects)
        qh_proj_quotas, qh_user_quotas = \
            quotas.get_projects_quota_limits()
        unsynced, unexpected = differences(local_proj_quotas, qh_proj_quotas)
        unsync_u, unexpect_u = differences(local_user_quotas, qh_user_quotas)
        unsynced += unsync_u
        unexpected += unexpect_u

        headers = ("Holder", "Source", "Resource", "Astakos", "Quotaholder")
        if not unsynced and (not check_unexpected or not unexpected):
            write("Everything in sync.\n")
            return

        printable = (unsynced if not check_unexpected
                     else unsynced + unexpected)
        pprint_table(self.stdout, printable, headers, title="Inconsistencies")
        if fix:
            to_sync = []
            for holder, source, resource, value, qh_value in unsynced:
                to_sync.append(((holder, source, resource), value))
            quotas.qh.set_quota(to_sync)

            if check_unexpected:
                to_del = []
                for holder, source, resource, value, qh_value in unexpected:
                    to_del.append((holder, source, resource))
                quotas.qh.delete_quota(to_del)

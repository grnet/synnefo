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
from django.db import transaction

from astakos.im.models import AstakosUser
from astakos.im.quotas import list_user_quotas
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management import utils
from astakos.im.management.commands import _common as common
from astakos.im.management.commands import _filtering as filtering
from django.db.models import Q, F

import logging
logger = logging.getLogger(__name__)


class Command(SynnefoCommand):
    help = "List user quota"

    option_list = SynnefoCommand.option_list + (
        make_option('--unit-style',
                    default='mb',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to mb") %
                    common.style_options),
        make_option('--overlimit',
                    action='store_true',
                    help="Show quota that is over limit"),
        make_option('--filter-by',
                    help="Filter by field; "
                    "e.g. \"user=uuid,usage>=10M,base_quota<inf\""),
        make_option('--display-mails',
                    action='store_true',
                    dest="display-mails",
                    help="Show user display name"),
    )

    QHFLT = {
        "limit": ("limit", filtering.parse_with_unit),
        "usage": ("usage_max", filtering.parse_with_unit),
        "user": ("holder", lambda x: x),
        "resource": ("resource", lambda x: x),
        "source": ("source", lambda x: x),
        }

    @transaction.commit_on_success
    def handle(self, *args, **options):
        output_format = options["output_format"]
        displayname = bool(options["display-mails"])
        unit_style = options["unit_style"]
        common.check_style(unit_style)

        filteropt = options["filter_by"]
        if filteropt is not None:
            filters = filteropt.split(",")
        else:
            filters = []

        QHQ = Q()
        for flt in filters:
            q = filtering.make_query(flt, self.QHFLT)
            if q is not None:
                QHQ &= q

        overlimit = bool(options["overlimit"])
        if overlimit:
            QHQ &= Q(usage_max__gt=F("limit"))

        users = AstakosUser.objects.accepted()
        qh_quotas = list_user_quotas(
            users, qhflt=QHQ)

        if displayname:
            info = {}
            for user in users:
                info[user.uuid] = user.email
        else:
            info = None

        print_data, labels = common.show_quotas(
            qh_quotas, info, style=unit_style)
        utils.pprint_table(self.stdout, print_data, labels, output_format)

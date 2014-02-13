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
        make_option('--displayname',
                    action='store_true',
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
        displayname = bool(options["displayname"])
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

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
#
import logging
from optparse import make_option

from synnefo.logic import reconciliation
from snf_django.management.commands import SynnefoCommand


HELP_MSG = """\
Check the consistency of pools of resources and fix them if possible.

This command checks that values that come from pools are not used more than
once. Also, it checks that are no stale reserved values in a pool by checking
that the reserved values are only the ones that are currently used.

The pools for the following resources are checked:
    * Pool of bridges
    * Pool of MAC prefixes
    * Pool of IPv4 addresses for each network"""


class Command(SynnefoCommand):
    help = HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option("--fix", action="store_true",
                    dest="fix", default=False,
                    help='Fix all issues.'),
    )

    def handle(self, **options):
        verbosity = int(options["verbosity"])
        fix = options["fix"]

        logger = logging.getLogger("reconcile-pools")
        logger.propagate = 0

        formatter = logging.Formatter("%(message)s")
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(formatter)
        if verbosity == 2:
            formatter = logging.Formatter("%(asctime)s: %(message)s")
            log_handler.setFormatter(formatter)
            logger.setLevel(logging.DEBUG)
        elif verbosity == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        logger.addHandler(log_handler)
        reconciler = reconciliation.PoolReconciler(logger=logger, fix=fix)
        reconciler.reconcile()

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
"""Reconciliation management command

Management command to reconcile the contents of the Synnefo DB with
the state of the Ganeti backend. See docstring on top of
logic/reconciliation.py for a description of reconciliation rules.

"""
import logging
from optparse import make_option

from synnefo.logic import reconciliation
from snf_django.management.commands import SynnefoCommand


class Command(SynnefoCommand):
    help = """Reconcile contents of Synnefo DB with state of Ganeti backend

Network reconciliation can detect and fix the following cases:
    - Missing database entries for a network in a Ganeti backend
    - Stale database networks, which do no exist in the Ganeti backend
    - Missing Ganeti networks
    - Ganeti networks that are not connected to all Ganeti nodegroups
    - Networks that have unsynced state
    - Orphan networks in the Ganeti backend
"""

    can_import_settings = True
    option_list = SynnefoCommand.option_list + (
        make_option('--fix-all', action='store_true',
                    dest='fix', default=False,
                    help='Fix all issues.'),
    )

    def handle(self, **options):
        verbosity = int(options["verbosity"])
        fix = options["fix"]

        logger = logging.getLogger("reconcile-networks")
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
        reconciler = reconciliation.NetworkReconciler(logger=logger, fix=fix)
        reconciler.reconcile_networks()

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
import sys
import logging
import subprocess
from optparse import make_option

from snf_django.management.commands import SynnefoCommand
from synnefo.management.common import get_resource
from synnefo.logic import reconciliation
from snf_django.management.utils import parse_bool


class Command(SynnefoCommand):
    can_import_settings = True
    umask = 0o007

    help = 'Reconcile contents of Synnefo DB with state of Ganeti backend'
    option_list = SynnefoCommand.option_list + (
        make_option('--backend-id', default=None, dest='backend-id',
                    help='Reconcilie VMs only for this backend'),
        make_option("--parallel",
                    dest="parallel",
                    default="True",
                    choices=["True", "False"],
                    metavar="True|False",
                    help="Perform server reconciliation for each backend"
                         " parallel."),
        make_option('--fix-stale', action='store_true', dest='fix_stale',
                    default=False, help='Fix (remove) stale DB entries in DB'),
        make_option('--fix-orphans', action='store_true', dest='fix_orphans',
                    default=False, help='Fix (remove) orphan Ganeti VMs'),
        make_option('--fix-unsynced', action='store_true', dest='fix_unsynced',
                    default=False, help='Fix server operstate in DB, set ' +
                                        'from Ganeti'),
        make_option('--fix-unsynced-nics', action='store_true',
                    dest='fix_unsynced_nics', default=False,
                    help='Fix unsynced nics between DB and Ganeti'),
        make_option('--fix-unsynced-disks', action='store_true',
                    dest='fix_unsynced_disks', default=False,
                    help='Fix unsynced disks between DB and Ganeti'),
        make_option('--fix-unsynced-flavors', action='store_true',
                    dest='fix_unsynced_flavors', default=False,
                    help='Fix unsynced flavors between DB and Ganeti'),
        make_option('--fix-pending-tasks', action='store_true',
                    dest='fix_pending_tasks', default=False,
                    help='Fix servers with stale pending tasks.'),
        make_option('--fix-unsynced-snapshots', action='store_true',
                    dest='fix_unsynced_snapshots', default=False,
                    help='Fix unsynced snapshots.'),
        make_option('--fix-all', action='store_true', dest='fix_all',
                    default=False, help='Enable all --fix-* arguments'),
    )

    def _process_args(self, options):
        keys_fix = [k for k in options.keys() if k.startswith('fix_')]
        if options['fix_all']:
            for kf in keys_fix:
                options[kf] = True

    def handle(self, **options):
        backend_id = options['backend-id']
        if backend_id:
            backends = [get_resource("backend", backend_id)]
        else:
            backends = reconciliation.get_online_backends()

        parallel = parse_bool(options["parallel"])
        if parallel and len(backends) > 1:
            cmd = sys.argv
            processes = []
            for backend in backends:
                p = subprocess.Popen(cmd + ["--backend-id=%s" % backend.id])
                processes.append(p)
            for p in processes:
                p.wait()
            return

        verbosity = int(options["verbosity"])

        logger = logging.getLogger("reconcile-servers")
        logger.propagate = 0

        formatter = logging.Formatter("%(message)s")
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(formatter)
        if verbosity == 2:
            formatter =\
                logging.Formatter("%(asctime)s [%(process)d]: %(message)s")
            log_handler.setFormatter(formatter)
            logger.setLevel(logging.DEBUG)
        elif verbosity == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        logger.addHandler(log_handler)

        self._process_args(options)

        for backend in backends:
            r = reconciliation.BackendReconciler(backend=backend,
                                                 logger=logger,
                                                 options=options)
            r.reconcile()

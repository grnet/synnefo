# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.
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
from django.core.management.base import BaseCommand
from synnefo.management.common import get_backend
from synnefo.logic import reconciliation
from synnefo.webproject.management.utils import parse_bool


class Command(BaseCommand):
    can_import_settings = True

    help = 'Reconcile contents of Synnefo DB with state of Ganeti backend'
    option_list = BaseCommand.option_list + (
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
        make_option('--fix-unsynced-flavors', action='store_true',
                    dest='fix_unsynced_flavors', default=False,
                    help='Fix unsynced flavors between DB and Ganeti'),
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
            backends = [get_backend(backend_id)]
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

        logger = logging.getLogger("reconcile-severs")
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

        self._process_args(options)

        for backend in backends:
            r = reconciliation.BackendReconciler(backend=backend,
                                                 logger=logger,
                                                 options=options)
            r.reconcile()

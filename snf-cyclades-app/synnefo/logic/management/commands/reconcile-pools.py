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
import logging
from optparse import make_option
from django.core.management.base import BaseCommand
from synnefo.logic import reconciliation


HELP_MSG = """\
Check the consistency of pools of resources and fix them if possible.

This command checks that values that come from pools are not used more than
once. Also, it checks that are no stale reserved values in a pool by checking
that the reserved values are only the ones that are currently used.

The pools for the following resources are checked:
    * Pool of bridges
    * Pool of MAC prefixes
    * Pool of IPv4 addresses for each network"""


class Command(BaseCommand):
    help = HELP_MSG

    option_list = BaseCommand.option_list + (
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

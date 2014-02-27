# Copyright 2012-2014 GRNET S.A. All rights reserved.
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

from django.core.management.base import BaseCommand, CommandError
from synnefo.management.common import get_resource
from snf_django.management.utils import parse_bool


from logging import getLogger
log = getLogger(__name__)


class Command(BaseCommand):
    args = "<flavor id>"
    help = "Modify a flavor"

    option_list = BaseCommand.option_list + (
        make_option(
            "--deleted",
            dest="deleted",
            metavar="True|False",
            choices=["True", "False"],
            default=None,
            help="Mark/unmark a flavor as deleted"),
        make_option(
            "--allow-create",
            dest="allow_create",
            metavar="True|False",
            choices=["True", "False"],
            default=None,
            help="Set if users can create servers with this flavor"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a flavor ID")

        flavor = get_resource("flavor", args[0], for_update=True)

        deleted = options['deleted']

        if deleted:
            deleted = parse_bool(deleted)
            log.info("Marking flavor %s as deleted=%s", flavor, deleted)
            flavor.deleted = deleted
            flavor.save()

        allow_create = options['allow_create']
        if allow_create:
            allow_create = parse_bool(allow_create)
            log.info("Marking flavor %s as allow_create=%s", flavor,
                     allow_create)
            flavor.allow_create = allow_create
            flavor.save()

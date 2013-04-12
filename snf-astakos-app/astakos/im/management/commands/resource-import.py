# Copyright 2013 GRNET S.A. All rights reserved.
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
from django.db.utils import IntegrityError
from django.utils import simplejson as json

from synnefo.lib.db.transaction import commit_on_success_strict
from astakos.im.resources import add_resources


class Command(BaseCommand):
    args = "<service> <resource> <desc> <unit>"
    help = "Import resources"

    option_list = BaseCommand.option_list + (
        make_option('--json',
                    dest='json',
                    metavar='<json.file>',
                    help="Load resource info from a json file"),
        make_option('--conf',
                    dest='conf',
                    metavar='<conf.json>',
                    help="Limit configuration file"),
    )

    @commit_on_success_strict()
    def handle(self, *args, **options):

        conf_file = options['conf']
        if not conf_file:
            m = "Please provide a configuation file."
            raise CommandError(m)

        with open(conf_file) as file_data:
            config = json.load(file_data)


        json_file = options['json']
        if json_file:
            with open(json_file) as file_data:
                data = json.load(file_data)

            service = data.get('service')
            resources = data.get('resources')
            if service is None or resources is None:
                m = "JSON file should contain service and resource data."
                raise CommandError(m)

            add_resources(service, resources, config)

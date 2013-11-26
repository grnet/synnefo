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
import json
import string
#from optparse import make_option

from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management.utils import pprint_table
#from astakos.im.models import AstakosUser, Resource
#from astakos.quotaholder_app.models import Holding
from astakos.admin import stats as statistics


class Command(SynnefoCommand):
    help = "Get available statistics of Astakos service"
    can_import_settings = True

    option_list = SynnefoCommand.option_list + (
    )

    def handle(self, *args, **options):
        stats = statistics.get_astakos_stats()

        output_format = options["output_format"]
        if output_format == "json":
            self.stdout.write(json.dumps(stats, indent=4) + "\n")
        elif output_format == "pretty":
            pretty_print_stats(stats, self.stdout)
        else:
            raise CommandError("Output format '%s' not supported." %
                               output_format)


def columns_from_fields(fields, values):
    return zip(map(string.lower, fields), [values.get(f, 0) for f in fields])


def pretty_print_stats(stats, stdout):
    newline = lambda: stdout.write("\n")

    _datetime = stats.get("datetime")
    stdout.write("datetime: %s\n" % _datetime)
    newline()

    users = stats.get("users", {})

    all_providers = users.pop("total")
    if all_providers is not None:
        fields = ["total", "verified", "active"]
        table = columns_from_fields(fields, all_providers)
        usage = all_providers.get("usage", {})
        for name, val in sorted(usage.items()):
            table.append((name, val))
        pprint_table(stdout, table, None,
                     title="Statistics for All Providers")
        newline()

    for provider_name, provider_info in sorted(users.items()):
        fields = ["total", "verified", "active"]
        table = columns_from_fields(fields, provider_info)
        usage = provider_info.get("usage", {})
        for name, val in sorted(usage.items()):
            table.append((name, val))
        pprint_table(stdout, table, None,
                     title="Statistics for Provider '%s'" % provider_name)
        newline()

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

import json
import string

from optparse import make_option

from snf_django.management.utils import pprint_table, parse_bool

from snf_django.management.commands import SynnefoCommand, CommandError
from synnefo.management.common import get_resource
from synnefo.admin import stats as statistics


class Command(SynnefoCommand):
    help = "Get available statistics of Cyclades service"
    can_import_settings = True

    command_option_list = (
        make_option("--backend",
                    dest="backend",
                    help="Include statistics only for this backend."),
        make_option("--clusters",
                    dest="clusters",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about clusters."),
        make_option("--servers",
                    dest="servers",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about servers."),
        make_option("--resources",
                    dest="resources",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about resources "
                         " (CPU, RAM, DISK)."),
        make_option("--networks",
                    dest="networks",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about networks."),
        make_option("--images",
                    dest="images",
                    default="False",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about images."),
    )

    def handle(self, *args, **options):
        if options["backend"] is not None:
            backend = get_resource("backend", options["backend"])
        else:
            backend = None

        clusters = parse_bool(options["clusters"])
        servers = parse_bool(options["servers"])
        resources = parse_bool(options["resources"])
        networks = parse_bool(options["networks"])
        images = parse_bool(options["images"])

        stats = statistics.get_cyclades_stats(backend, clusters, servers,
                                              resources, networks, images)

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

    clusters = stats.get("clusters")
    if clusters is not None:
        fields = ["total", "drained", "offline"]
        table = columns_from_fields(fields, clusters)
        pprint_table(stdout, table, None,
                     title="Statistics for Ganeti Clusters")
        newline()

    servers = stats.get("servers")
    if servers is not None:
        fields = ["total", "STARTED", "STOPPED", "BUILD", "ERROR", "DESTROYED"]
        table = columns_from_fields(fields, servers)
        pprint_table(stdout, table, None,
                     title="Statistics for Virtual Servers")
        newline()

    networks = stats.get("networks")
    if networks is not None:
        public_ips = networks.pop("public_ips")
        networks["total_public_ips"] = public_ips.get("total", 0)
        networks["free_public_ips"] = public_ips.get("free", 0)
        fields = ["total", "ACTIVE", "DELETED", "ERROR", "total_public_ips",
                  "free_public_ips"]
        table = columns_from_fields(fields, networks)
        pprint_table(stdout, table, None,
                     title="Statistics for Virtual Networks")
        newline()

    resources = stats.get("resources")
    if resources is not None:
        for resource_name, resource in sorted(resources.items()):
            fields = ["total", "allocated"]
            for res, num in sorted(resource.pop("servers", {}).items()):
                name = "servers_with_%s" % res
                resource[name] = num
                fields.append(name)
            table = columns_from_fields(fields, resource)
            pprint_table(stdout, table, None,
                         title="Statistics for %s" % resource_name)
            newline()

    images = stats.get("images")
    if images is not None:
        pprint_table(stdout, sorted(images.items()), None,
                     title="Statistics for Images")
        newline()

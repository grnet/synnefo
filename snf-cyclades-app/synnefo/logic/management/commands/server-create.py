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

from django.core.management.base import CommandError

from synnefo.management import common, pprint
from snf_django.management.utils import parse_bool
from snf_django.management.commands import SynnefoCommand

from synnefo.logic import servers

HELP_MSG = """

Create a new VM without authenticating the user or checking the resource
limits of the user. Also the allocator can be bypassed by specifing a
backend-id.
"""


class Command(SynnefoCommand):
    help = "Create a new VM." + HELP_MSG

    option_list = SynnefoCommand.option_list + (
        make_option("--backend-id", dest="backend_id",
                    help="Unique identifier of the Ganeti backend."
                         " Use snf-manage backend-list to find out"
                         " available backends."),
        make_option("--name", dest="name",
                    help="An arbitrary string for naming the server"),
        make_option("--user-id", dest="user_id",
                    help="Unique identifier of the owner of the server"),
        make_option("--image-id", dest="image_id",
                    help="Unique identifier of the image."
                         " Use snf-manage image-list to find out"
                         " available images."),
        make_option("--flavor-id", dest="flavor_id",
                    help="Unique identifier of the flavor"
                         " Use snf-manage flavor-list to find out"
                         " available flavors."),
        make_option("--password", dest="password",
                    help="Password for the new server"),
        make_option("--port", dest="connections", action="append",
                    help="--port network:<network_id>(,address=<ip_address>),"
                         " --port id:<port_id>"
                         " --port floatingip:<floatingip_id>."),
        make_option("--volume", dest="volumes", action="append",
                    help="--volume size=<size>, --volume id=<volume_id"
                         ", --volume size=<size>,image=<image_id>"
                         ", --volume size=<size>,snapshot=<snapshot_id>",
                    default=[]),
        make_option("--floating-ips", dest="floating_ip_ids",
                    help="Comma separated list of port IDs to connect"),
        make_option(
            '--wait',
            dest='wait',
            default="False",
            choices=["True", "False"],
            metavar="True|False",
            help="Wait for Ganeti job to complete."),

    )

    @common.convert_api_faults
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        name = options['name']
        user_id = options['user_id']
        backend_id = options['backend_id']
        image_id = options['image_id']
        flavor_id = options['flavor_id']
        password = options['password']

        if not name:
            raise CommandError("name is mandatory")
        if not user_id:
            raise CommandError("user-id is mandatory")
        if not password:
            raise CommandError("password is mandatory")
        if not flavor_id:
            raise CommandError("flavor-id is mandatory")
        if not image_id:
            raise CommandError("image-id is mandatory")

        flavor = common.get_resource("flavor", flavor_id)
        image = common.get_image(image_id, user_id)
        if backend_id:
            backend = common.get_resource("backend", backend_id)
        else:
            backend = None

        connection_list = parse_connections(options["connections"])
        volumes_list = parse_volumes(options["volumes"])
        server = servers.create(user_id, name, password, flavor, image["id"],
                                networks=connection_list,
                                volumes=volumes_list,
                                use_backend=backend)
        pprint.pprint_server(server, stdout=self.stdout)

        wait = parse_bool(options["wait"])
        common.wait_server_task(server, wait, self.stdout)


def parse_volumes(vol_list):
    volumes = []
    for vol in vol_list:
        vol_dict = {}
        kv_list = vol.split(",")
        for kv_item in kv_list:
            try:
                k, v = kv_item.split("=")
            except (TypeError, ValueError):
                raise CommandError("Invalid syntax for volume: %s" % vol)
            vol_dict[k] = v
        size = vol_dict.get("size")
        if size is not None:
            try:
                size = int(size)
            except (TypeError, ValueError):
                raise CommandError("Invalid size: %s" % size)
        if len(vol_dict) == 1:
            if size is not None:
                volumes.append({"size": size, "source_type": "blank",
                                "source_uuid": None})
                continue
            vol_id = vol_dict.get("id")
            if vol_id is not None:
                volumes.append({"source_uuid": vol_id,
                                "source_type": "volume"})
                continue
            raise CommandError("Invalid syntax for volume %s" % vol)
        image = vol_dict.get("image")
        snapshot = vol_dict.get("snapshot")
        if image and snapshot or not(image or snapshot) or size is None:
            raise CommandError("Invalid syntax for volume %s" % vol)
        source = image if image else snapshot
        source_type = "image" if image else "snapshot"
        volumes.append({"source_uuid": source,
                        "source_type": source_type,
                        "size": size})
    return volumes


def parse_connections(con_list):
    connections = []
    if con_list:
        for opt in con_list:
            try:
                con_kind = opt.split(":")[0]
                if con_kind == "network":
                    info = opt.split(",")
                    network_id = info[0].split(":")[1]
                    try:
                        address = info[1].split(":")[1]
                    except:
                        address = None
                    if address:
                        val = {"uuid": network_id, "fixed_ip": address}
                    else:
                        val = {"uuid": network_id}
                elif con_kind == "id":
                    port_id = opt.split(":")[1]
                    val = {"port": port_id}
                elif con_kind == "floatingip":
                    fip_id = opt.split(":")[1]
                    fip = common.get_resource("floating-ip", fip_id,
                                              for_update=True)
                    val = {"uuid": fip.network_id, "fixed_ip": fip.address}
                else:
                    raise CommandError("Unknown argument for option --port")

                connections.append(val)
            except:
                raise CommandError("Malformed information for option --port")
    return connections

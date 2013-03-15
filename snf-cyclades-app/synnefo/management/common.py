# Copyright 2012 GRNET S.A. All rights reserved.
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

from django.core.management import CommandError
from synnefo.db.models import Backend, VirtualMachine, Network, Flavor
from synnefo.api.util import get_image as backend_get_image
from synnefo.api.faults import ItemNotFound, BadRequest, OverLimit

from synnefo.api.util import validate_network_params
from synnefo.settings import (CYCLADES_ASTAKOS_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_URL)
from synnefo.logic.rapi import GanetiApiError, GanetiRapiClient
from synnefo.logic.utils import (id_from_instance_name,
                                 id_from_network_name)
from synnefo.lib import astakos

import logging
log = logging.getLogger(__name__)


def format_vm_state(vm):
    if vm.operstate == "BUILD":
        return "BUILD(" + str(vm.buildpercentage) + "%)"
    else:
        return vm.operstate


def validate_network_info(options):
    subnet = options['subnet']
    gateway = options['gateway']
    subnet6 = options['subnet6']
    gateway6 = options['gateway6']

    try:
        validate_network_params(subnet, gateway)
    except (BadRequest, OverLimit) as e:
        raise CommandError(e)

    return subnet, gateway, subnet6, gateway6


def get_backend(backend_id):
    try:
        backend_id = int(backend_id)
        return Backend.objects.get(id=backend_id)
    except ValueError:
        raise CommandError("Invalid Backend ID: %s" % backend_id)
    except Backend.DoesNotExist:
        raise CommandError("Backend with ID %s not found in DB. "
                           " Use snf-manage backend-list to find"
                           " out available backend IDs." % backend_id)


def get_image(image_id, user_id):
    if image_id:
        try:
            return backend_get_image(image_id, user_id)
        except ItemNotFound:
            raise CommandError("Image with ID %s not found."
                               " Use snf-manage image-list to find"
                               " out available image IDs." % image_id)
    else:
        raise CommandError("image-id is mandatory")


def get_vm(server_id):
    """Get a VirtualMachine object by its ID.

    @type server_id: int or string
    @param server_id: The server's DB id or the Ganeti name

    """
    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        try:
            server_id = id_from_instance_name(server_id)
        except VirtualMachine.InvalidBackendIdError:
            raise CommandError("Invalid server ID: %s" % server_id)

    try:
        return VirtualMachine.objects.get(id=server_id)
    except VirtualMachine.DoesNotExist:
        raise CommandError("Server with ID %s not found in DB."
                           " Use snf-manage server-list to find out"
                           " available server IDs." % server_id)


def get_network(network_id):
    """Get a Network object by its ID.

    @type network_id: int or string
    @param network_id: The networks DB id or the Ganeti name

    """

    try:
        network_id = int(network_id)
    except (ValueError, TypeError):
        try:
            network_id = id_from_network_name(network_id)
        except Network.InvalidBackendIdError:
            raise CommandError("Invalid network ID: %s" % network_id)

    try:
        return Network.objects.get(id=network_id)
    except Network.DoesNotExist:
        raise CommandError("Network with ID %s not found in DB."
                           " Use snf-manage network-list to find out"
                           " available network IDs." % network_id)


def get_flavor(flavor_id):
    try:
        flavor_id = int(flavor_id)
        return Flavor.objects.get(id=flavor_id)
    except ValueError:
        raise CommandError("Invalid flavor ID: %s", flavor_id)
    except Flavor.DoesNotExist:
        raise CommandError("Flavor with ID %s not found in DB."
                           " Use snf-manage flavor-list to find out"
                           " available flavor IDs." % flavor_id)


def check_backend_credentials(clustername, port, username, password):
    try:
        client = GanetiRapiClient(clustername, port, username, password)
        # This command will raise an exception if there is no
        # write-access
        client.ModifyCluster()
    except GanetiApiError as e:
        raise CommandError(e)

    info = client.GetInfo()
    info_name = info['name']
    if info_name != clustername:
        raise CommandError("Invalid clustername value. Please use the"
                           " Ganeti Cluster name: %s" % info_name)


class UserCache(object):
    """uuid<->displayname user 'cache'"""

    user_catalogs_url = ASTAKOS_URL.replace("im/authenticate",
                                            "service/api/user_catalogs")

    def __init__(self, split=100):
        self.users = {}

        self.split = split
        assert(self.split > 0), "split must be positive"

    def fetch_names(self, uuid_list):
        total = len(uuid_list)
        split = self.split

        for start in range(0, total, split):
            end = start + split
            try:
                names = \
                    astakos.get_displaynames(token=ASTAKOS_TOKEN,
                                             url=UserCache.user_catalogs_url,
                                             uuids=uuid_list[start:end])
                self.users.update(names)
            except Exception as e:
                log.error("Failed to fetch names: %s",  e)

    def get_uuid(self, name):
        if not name in self.users:
            try:
                self.users[name] = \
                    astakos.get_user_uuid(token=ASTAKOS_TOKEN,
                                          url=UserCache.user_catalogs_url,
                                          displayname=name)
            except Exception as e:
                log.error("Can not get uuid for name %s: %s", name, e)
                self.users[name] = name

        return self.users[name]

    def get_name(self, uuid):
        """Do the uuid-to-email resolving"""

        if not uuid in self.users:
            try:
                self.users[uuid] = \
                    astakos.get_displayname(token=ASTAKOS_TOKEN,
                                            url=UserCache.user_catalogs_url,
                                            uuid=uuid)
            except Exception as e:
                log.error("Can not get display name for uuid %s: %s", uuid, e)
                self.users[uuid] = "-"

        return self.users[uuid]


class Omit(object):
    pass

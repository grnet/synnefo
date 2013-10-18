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

from django.core.management import CommandError
from synnefo.db.models import (Backend, VirtualMachine, Network,
                               Flavor, IPAddress, Subnet,
                               BridgePoolTable, MacPrefixPoolTable,
                               NetworkInterface, Volume)
from functools import wraps

from django.conf import settings
from snf_django.lib.api import faults
from synnefo.api import util
from synnefo.logic import backend as backend_mod
from synnefo.logic.rapi import GanetiApiError, GanetiRapiClient
from synnefo.logic.utils import (id_from_instance_name,
                                 id_from_network_name,
                                 id_from_nic_name)
from django.core.exceptions import ObjectDoesNotExist
import logging
log = logging.getLogger(__name__)


def format_vm_state(vm):
    if vm.operstate == "BUILD":
        return "BUILD(" + str(vm.buildpercentage) + "%)"
    else:
        return vm.operstate

RESOURCE_MAP = {
    "backend": Backend.objects,
    "flavor": Flavor.objects,
    "server": VirtualMachine.objects,
    "volume": Volume.objects,
    "network": Network.objects,
    "subnet": Subnet.objects,
    "port": NetworkInterface.objects,
    "floating-ip": IPAddress.objects.filter(floating_ip=True)}


def get_resource(name, value, for_update=False):
    """Get object from DB based by it's ID

    Helper function for getting an object from DB by it's DB and raising
    appropriate command line errors if the object does not exist or the
    ID is invalid.

    """
    objects = RESOURCE_MAP[name]
    if name == "floating-ip":
        capital_name = "Floating IP"
    else:
        capital_name = name.capitalize()

    if isinstance(value, basestring) and name in ["server", "network", "port"]:
        if value.startswith(settings.BACKEND_PREFIX_ID):
            try:
                if name == "server":
                    value = id_from_instance_name(value)
                elif name == "network":
                    value = id_from_network_name(value)
                elif name == "port":
                    value = id_from_nic_name(value)
            except ValueError:
                raise CommandError("Invalid {} ID: {}".format(capital_name,
                                                              value))

    if for_update:
        objects = objects.select_for_update()
    try:
        return objects.get(id=value)
    except ObjectDoesNotExist:
        msg = ("{0} with ID {1} does not exist. Use {2}-list to find out"
               " available {2} IDs.")
        raise CommandError(msg.format(capital_name, value, name))
    except (ValueError, TypeError):
        raise CommandError("Invalid {} ID: {}".format(capital_name, value))


def get_image(image_id, user_id):
    if image_id:
        try:
            return util.get_image_dict(image_id, user_id)
        except faults.ItemNotFound:
            raise CommandError("Image with ID %s not found."
                               " Use snf-manage image-list to find"
                               " out available image IDs." % image_id)
    else:
        raise CommandError("image-id is mandatory")


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


def convert_api_faults(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except faults.Fault as e:
            raise CommandError(e.message)
    return wrapper


class Omit(object):
    pass


def wait_server_task(server, wait, stdout):
    jobID = server.task_job_id
    if jobID is None:
        return
    if wait:
        msg = "Issued job '%s'. Waiting to complete...\n"
        stdout.write(msg % jobID)
        client = server.get_client()
        wait_ganeti_job(client, jobID, stdout)
    else:
        msg = "Issued job '%s'.\n"
        stdout.write(msg % jobID)


def wait_ganeti_job(client, jobID, stdout):
    status, error = backend_mod.wait_for_job(client, jobID)
    if status == "success":
        stdout.write("Job finished successfully.\n")
    else:
        raise CommandError("Job failed! Error: %s\n" % error)


def pool_table_from_type(type_):
    if type_ == "mac-prefix":
        return MacPrefixPoolTable
    elif type_ == "bridge":
        return BridgePoolTable
    # elif type == "ip":
    #     return IPPoolTable
    else:
        raise ValueError("Invalid pool type")

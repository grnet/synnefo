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

from base64 import urlsafe_b64encode, b64decode
from urllib import quote
from hashlib import sha256
from logging import getLogger
from random import choice
from string import digits, lowercase, uppercase

from Crypto.Cipher import AES

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.db.models import Q

from snf_django.lib.api import faults
from synnefo.db.models import (Flavor, VirtualMachine, VirtualMachineMetadata,
                               Network, NetworkInterface, SecurityGroup,
                               BridgePoolTable, MacPrefixPoolTable, IPAddress,
                               IPPoolTable)
from synnefo.plankton.backend import PlanktonBackend

from synnefo.cyclades_settings import cyclades_services, BASE_HOST
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

COMPUTE_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "compute", version="v2.0"))
SERVERS_URL = join_urls(COMPUTE_URL, "servers/")
FLAVORS_URL = join_urls(COMPUTE_URL, "flavors/")
IMAGES_URL = join_urls(COMPUTE_URL, "images/")
PLANKTON_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "image", version="v1.0"))
IMAGES_PLANKTON_URL = join_urls(PLANKTON_URL, "images/")

NETWORK_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "network", version="v2.0"))
NETWORKS_URL = join_urls(NETWORK_URL, "networks/")
PORTS_URL = join_urls(NETWORK_URL, "ports/")
SUBNETS_URL = join_urls(NETWORK_URL, "subnets/")
FLOATING_IPS_URL = join_urls(NETWORK_URL, "floatingips/")

PITHOSMAP_PREFIX = "pithosmap://"

log = getLogger('synnefo.api')


def random_password():
    """Generates a random password

    We generate a windows compliant password: it must contain at least
    one charachter from each of the groups: upper case, lower case, digits.
    """

    pool = lowercase + uppercase + digits
    lowerset = set(lowercase)
    upperset = set(uppercase)
    digitset = set(digits)
    length = 10

    password = ''.join(choice(pool) for i in range(length - 2))

    # Make sure the password is compliant
    chars = set(password)
    if not chars & lowerset:
        password += choice(lowercase)
    if not chars & upperset:
        password += choice(uppercase)
    if not chars & digitset:
        password += choice(digits)

    # Pad if necessary to reach required length
    password += ''.join(choice(pool) for i in range(length - len(password)))

    return password


def zeropad(s):
    """Add zeros at the end of a string in order to make its length
       a multiple of 16."""

    npad = 16 - len(s) % 16
    return s + '\x00' * npad


def stats_encrypt(plaintext):
    # Make sure key is 32 bytes long
    key = sha256(settings.CYCLADES_STATS_SECRET_KEY).digest()

    aes = AES.new(key)
    enc = aes.encrypt(zeropad(plaintext))
    return quote(urlsafe_b64encode(enc))


def get_vm(server_id, user_id, for_update=False, non_deleted=False,
           non_suspended=False, prefetch_related=None):
    """Find a VirtualMachine instance based on ID and owner."""

    try:
        server_id = int(server_id)
        servers = VirtualMachine.objects
        if for_update:
            servers = servers.select_for_update()
        if prefetch_related is not None:
            if isinstance(prefetch_related, list):
                servers = servers.prefetch_related(*prefetch_related)
            else:
                servers = servers.prefetch_related(prefetch_related)
        vm = servers.get(id=server_id, userid=user_id)
        if non_deleted and vm.deleted:
            raise faults.BadRequest("Server has been deleted.")
        if non_suspended and vm.suspended:
            raise faults.Forbidden("Administratively Suspended VM")
        return vm
    except (ValueError, TypeError):
        raise faults.BadRequest('Invalid server ID.')
    except VirtualMachine.DoesNotExist:
        raise faults.ItemNotFound('Server not found.')


def get_vm_meta(vm, key):
    """Return a VirtualMachineMetadata instance or raise ItemNotFound."""

    try:
        return VirtualMachineMetadata.objects.get(meta_key=key, vm=vm)
    except VirtualMachineMetadata.DoesNotExist:
        raise faults.ItemNotFound('Metadata key not found.')


def get_image(image_id, user_id):
    """Return an Image instance or raise ItemNotFound."""

    with PlanktonBackend(user_id) as backend:
        return backend.get_image(image_id)


def get_image_dict(image_id, user_id):
    image = {}
    img = get_image(image_id, user_id)
    image["id"] = img["id"]
    image["name"] = img["name"]
    image["format"] = img["disk_format"]
    image["location"] = img["location"]
    image["is_snapshot"] = img["is_snapshot"]
    image["status"] = img["status"]
    size = image["size"] = img["size"]

    mapfile = img["mapfile"]
    if mapfile.startswith("archip:"):
        _, unprefixed_mapfile, = mapfile.split("archip:")
        mapfile = unprefixed_mapfile
    else:
        unprefixed_mapfile = mapfile
        mapfile = "pithos:" + mapfile

    image["backend_id"] = PITHOSMAP_PREFIX + "/".join([unprefixed_mapfile,
                                                       str(size)])
    image["mapfile"] = mapfile

    properties = img.get("properties", {})
    image["metadata"] = dict((key.upper(), val)
                             for key, val in properties.items())

    return image


def get_flavor(flavor_id, include_deleted=False):
    """Return a Flavor instance or raise ItemNotFound."""

    try:
        flavor_id = int(flavor_id)
        flavors = Flavor.objects.select_related("volume_type")
        if not include_deleted:
            flavors = flavors.filter(deleted=False)
        return flavors.get(id=flavor_id)
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid flavor ID '%s'" % flavor_id)
    except Flavor.DoesNotExist:
        raise faults.ItemNotFound('Flavor not found.')


def get_network(network_id, user_id, for_update=False, non_deleted=False):
    """Return a Network instance or raise ItemNotFound."""

    try:
        network_id = int(network_id)
        objects = Network.objects
        if for_update:
            objects = objects.select_for_update()
        network = objects.get(Q(userid=user_id) | Q(public=True),
                              id=network_id)
        if non_deleted and network.deleted:
            raise faults.BadRequest("Network has been deleted.")
        return network
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid network ID '%s'" % network_id)
    except Network.DoesNotExist:
        raise faults.ItemNotFound('Network %s not found.' % network_id)


def get_port(port_id, user_id, for_update=False):
    """
    Return a NetworkInteface instance or raise ItemNotFound.
    """
    try:
        objects = NetworkInterface.objects.filter(userid=user_id)
        if for_update:
            objects = objects.select_for_update()
        # if (port.device_owner != "vm") and for_update:
        #     raise faults.BadRequest('Cannot update non vm port')
        return objects.get(id=port_id)
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid port ID '%s'" % port_id)
    except NetworkInterface.DoesNotExist:
        raise faults.ItemNotFound("Port '%s' not found." % port_id)


def get_security_group(sg_id):
    try:
        sg = SecurityGroup.objects.get(id=sg_id)
        return sg
    except (ValueError, SecurityGroup.DoesNotExist):
        raise faults.ItemNotFound("Not valid security group")


def get_floating_ip_by_address(userid, address, for_update=False):
    try:
        objects = IPAddress.objects
        if for_update:
            objects = objects.select_for_update()
        return objects.get(userid=userid, floating_ip=True,
                           address=address, deleted=False)
    except IPAddress.DoesNotExist:
        raise faults.ItemNotFound("Floating IP does not exist.")


def get_floating_ip_by_id(userid, floating_ip_id, for_update=False):
    try:
        floating_ip_id = int(floating_ip_id)
        objects = IPAddress.objects
        if for_update:
            objects = objects.select_for_update()
        return objects.get(id=floating_ip_id, floating_ip=True,
                           userid=userid, deleted=False)
    except IPAddress.DoesNotExist:
        raise faults.ItemNotFound("Floating IP with ID %s does not exist." %
                                  floating_ip_id)
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid Floating IP ID %s" % floating_ip_id)


def backend_has_free_public_ip(backend):
    """Check if a backend has a free public IPv4 address."""
    ip_pool_rows = IPPoolTable.objects.select_for_update()\
        .filter(subnet__network__public=True)\
        .filter(subnet__network__drained=False)\
        .filter(subnet__deleted=False)\
        .filter(subnet__network__backend_networks__backend=backend)
    for pool_row in ip_pool_rows:
        pool = pool_row.pool
        if pool.empty():
            continue
        else:
            return True


def backend_public_networks(backend):
    return Network.objects.filter(deleted=False, public=True,
                                  backend_networks__backend=backend)


def get_vm_nic(vm, nic_id):
    """Get a VMs NIC by its ID."""
    try:
        nic_id = int(nic_id)
        return vm.nics.get(id=nic_id)
    except NetworkInterface.DoesNotExist:
        raise faults.ItemNotFound("NIC '%s' not found" % nic_id)
    except (ValueError, TypeError):
        raise faults.BadRequest("Invalid NIC ID '%s'" % nic_id)


def get_nic(nic_id):
    try:
        return NetworkInterface.objects.get(id=nic_id)
    except NetworkInterface.DoesNotExist:
        raise faults.ItemNotFound("NIC '%s' not found" % nic_id)


def render_metadata(request, metadata, use_values=False, status=200):
    if request.serialization == 'xml':
        data = render_to_string('metadata.xml', {'metadata': metadata})
    else:
        if use_values:
            d = {'metadata': {'values': metadata}}
        else:
            d = {'metadata': metadata}
        data = json.dumps(d)
    return HttpResponse(data, status=status)


def render_meta(request, meta, status=200):
    if request.serialization == 'xml':
        key, val = meta.items()[0]
        data = render_to_string('meta.xml', dict(key=key, val=val))
    else:
        data = json.dumps(dict(meta=meta))
    return HttpResponse(data, status=status)


def verify_personality(personality):
    """Verify that a a list of personalities is well formed"""
    if len(personality) > settings.MAX_PERSONALITY:
        raise faults.OverLimit("Maximum number of personalities"
                               " exceeded")
    for p in personality:
        # Verify that personalities are well-formed
        try:
            assert isinstance(p, dict)
            keys = set(p.keys())
            allowed = set(['contents', 'group', 'mode', 'owner', 'path'])
            assert keys.issubset(allowed)
            contents = p['contents']
            if len(contents) > settings.MAX_PERSONALITY_SIZE:
                # No need to decode if contents already exceed limit
                raise faults.OverLimit("Maximum size of personality exceeded")
            if len(b64decode(contents)) > settings.MAX_PERSONALITY_SIZE:
                raise faults.OverLimit("Maximum size of personality exceeded")
        except (AssertionError, TypeError):
            raise faults.BadRequest("Malformed personality in request")


def values_from_flavor(flavor):
    """Get Ganeti connectivity info from flavor type.

    If link or mac_prefix equals to "pool", then the resources
    are allocated from the corresponding Pools.

    """
    try:
        flavor = Network.FLAVORS[flavor]
    except KeyError:
        raise faults.BadRequest("Unknown network flavor")

    mode = flavor.get("mode")

    link = flavor.get("link")
    if link == "pool":
        link = allocate_resource("bridge")

    mac_prefix = flavor.get("mac_prefix")
    if mac_prefix == "pool":
        mac_prefix = allocate_resource("mac_prefix")

    tags = flavor.get("tags")

    return mode, link, mac_prefix, tags


def allocate_resource(res_type):
    table = get_pool_table(res_type)
    pool = table.get_pool()
    value = pool.get()
    pool.save()
    return value


def release_resource(res_type, value):
    table = get_pool_table(res_type)
    pool = table.get_pool()
    pool.put(value)
    pool.save()


def get_pool_table(res_type):
    if res_type == "bridge":
        return BridgePoolTable
    elif res_type == "mac_prefix":
        return MacPrefixPoolTable
    else:
        raise Exception("Unknown resource type")


def get_existing_users():
    """
    Retrieve user ids stored in cyclades user agnostic models.
    """
    # also check PublicKeys a user with no servers/networks exist
    from synnefo.userdata.models import PublicKeyPair
    from synnefo.db.models import VirtualMachine, Network

    keypairusernames = PublicKeyPair.objects.filter().values_list('user',
                                                                  flat=True)
    serverusernames = VirtualMachine.objects.filter().values_list('userid',
                                                                  flat=True)
    networkusernames = Network.objects.filter().values_list('userid',
                                                            flat=True)

    return set(list(keypairusernames) + list(serverusernames) +
               list(networkusernames))


def vm_to_links(vm_id):
    href = join_urls(SERVERS_URL, str(vm_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def network_to_links(network_id):
    href = join_urls(NETWORKS_URL, str(network_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def subnet_to_links(subnet_id):
    href = join_urls(SUBNETS_URL, str(subnet_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def port_to_links(port_id):
    href = join_urls(PORTS_URL, str(port_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def flavor_to_links(flavor_id):
    href = join_urls(FLAVORS_URL, str(flavor_id))
    return [{"rel": rel, "href": href} for rel in ("self", "bookmark")]


def image_to_links(image_id):
    href = join_urls(IMAGES_URL, str(image_id))
    links = [{"rel": rel, "href": href} for rel in ("self", "bookmark")]
    links.append({"rel": "alternate",
                  "href": join_urls(IMAGES_PLANKTON_URL, str(image_id))})
    return links


def start_action(vm, action, jobId):
    vm.action = action
    vm.backendjobid = jobId
    vm.backendopcode = None
    vm.backendjobstatus = None
    vm.backendlogmsg = None
    vm.save()

# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from base64 import b64encode, b64decode
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
                               Network, BackendNetwork, NetworkInterface,
                               BridgePoolTable, MacPrefixPoolTable, Backend,
                               IPAddress)
from synnefo.db.pools import EmptyPool

from synnefo.plankton.utils import image_backend

from synnefo.cyclades_settings import cyclades_services, BASE_HOST
from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

COMPUTE_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "compute", version="v2.0"))
SERVERS_URL = join_urls(COMPUTE_URL, "servers/")
NETWORKS_URL = join_urls(COMPUTE_URL, "networks/")
FLAVORS_URL = join_urls(COMPUTE_URL, "flavors/")
IMAGES_URL = join_urls(COMPUTE_URL, "images/")
PLANKTON_URL = \
    join_urls(BASE_HOST,
              get_service_path(cyclades_services, "image", version="v1.0"))
IMAGES_PLANKTON_URL = join_urls(PLANKTON_URL, "images/")

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


def encrypt(plaintext):
    # Make sure key is 32 bytes long
    key = sha256(settings.SECRET_KEY).digest()

    aes = AES.new(key)
    enc = aes.encrypt(zeropad(plaintext))
    return b64encode(enc)


def get_vm(server_id, user_id, for_update=False, non_deleted=False,
           non_suspended=False):
    """Find a VirtualMachine instance based on ID and owner."""

    try:
        server_id = int(server_id)
        servers = VirtualMachine.objects
        if for_update:
            servers = servers.select_for_update()
        vm = servers.get(id=server_id, userid=user_id)
        if non_deleted and vm.deleted:
            raise faults.BadRequest("Server has been deleted.")
        if non_suspended and vm.suspended:
            raise faults.Forbidden("Administratively Suspended VM")
        return vm
    except ValueError:
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

    with image_backend(user_id) as backend:
        return backend.get_image(image_id)


def get_image_dict(image_id, user_id):
    image = {}
    img = get_image(image_id, user_id)
    image["id"] = img["id"]
    image["name"] = img["name"]
    image["format"] = img["disk_format"]
    image["checksum"] = img["checksum"]
    image["location"] = img["location"]

    checksum = image["checksum"] = img["checksum"]
    size = image["size"] = img["size"]
    image["backend_id"] = PITHOSMAP_PREFIX + "/".join([checksum, str(size)])

    properties = img.get("properties", {})
    image["metadata"] = dict((key.upper(), val)
                             for key, val in properties.items())

    return image


def get_flavor(flavor_id, include_deleted=False):
    """Return a Flavor instance or raise ItemNotFound."""

    try:
        flavor_id = int(flavor_id)
        if include_deleted:
            return Flavor.objects.get(id=flavor_id)
        else:
            return Flavor.objects.get(id=flavor_id, deleted=include_deleted)
    except (ValueError, Flavor.DoesNotExist):
        raise faults.ItemNotFound('Flavor not found.')


def get_flavor_provider(flavor):
    """Extract provider from disk template.

    Provider for `ext` disk_template is encoded in the disk template
    name, which is formed `ext_<provider_name>`. Provider is None
    for all other disk templates.

    """
    disk_template = flavor.disk_template
    provider = None
    if disk_template.startswith("ext"):
        disk_template, provider = disk_template.split("_", 1)
    return disk_template, provider


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
    except (ValueError, Network.DoesNotExist):
        raise faults.ItemNotFound('Network not found.')


def get_floating_ip(user_id, ipv4, for_update=False):
    try:
        objects = IPAddress.objects
        if for_update:
            objects = objects.select_for_update()
        return objects.get(userid=user_id, ipv4=ipv4, deleted=False)
    except IPAddress.DoesNotExist:
        raise faults.ItemNotFound("Floating IP does not exist.")


def allocate_public_address(backend, userid):
    """Get a public IP for any available network of a backend."""
    # Guarantee exclusive access to backend, because accessing the IP pools of
    # the backend networks may result in a deadlock with backend allocator
    # which also checks that backend networks have a free IP.
    backend = Backend.objects.select_for_update().get(id=backend.id)
    public_networks = backend_public_networks(backend)
    return get_free_ip(public_networks, userid)


def backend_public_networks(backend):
    """Return available public networks of the backend.

    Iterator for non-deleted public networks that are available
    to the specified backend.

    """
    bnets = BackendNetwork.objects.filter(backend=backend,
                                          network__public=True,
                                          network__deleted=False,
                                          network__floating_ip_pool=False,
                                          network__drained=False)
    return [b.network for b in bnets]


def get_free_ip(networks, userid):
    for network in networks:
        try:
            return network.allocate_address(userid=userid)
        except faults.OverLimit:
            pass
    msg = "Can not allocate public IP. Public networks are full."
    log.error(msg)
    raise faults.OverLimit(msg)


def get_network_free_address(network, userid):
    """Reserve an IP address from the IP Pool of the network."""

    try:
        return network.allocate_address(userid=userid)
    except EmptyPool:
        raise faults.OverLimit("Network %s is full." % network.backend_id)


def get_vm_nic(vm, nic_id):
    """Get a VMs NIC by its ID."""
    try:
        return vm.nics.get(id=nic_id)
    except NetworkInterface.DoesNotExist:
        raise faults.ItemNotFound("NIC '%s' not found" % nic_id)


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
        except AssertionError:
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

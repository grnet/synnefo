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

import datetime

from base64 import b64encode, b64decode
from datetime import timedelta, tzinfo
from functools import wraps
from hashlib import sha256
from logging import getLogger
from random import choice
from string import digits, lowercase, uppercase
from time import time
from traceback import format_exc
from wsgiref.handlers import format_date_time

import dateutil.parser

from Crypto.Cipher import AES

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.cache import add_never_cache_headers
from django.db.models import Q

from synnefo.api.faults import (Fault, BadRequest, BuildInProgress,
                                ItemNotFound, ServiceUnavailable, Unauthorized,
                                BadMediaType, Forbidden, OverLimit)
from synnefo.db.models import (Flavor, VirtualMachine, VirtualMachineMetadata,
                               Network, BackendNetwork, NetworkInterface,
                               BridgePoolTable, MacPrefixPoolTable)
from synnefo.db.pools import EmptyPool

from synnefo.lib.astakos import get_user
from synnefo.plankton.backend import ImageBackend, NotAllowedError
from synnefo.settings import MAX_CIDR_BLOCK


log = getLogger('synnefo.api')


class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return timedelta(0)


def isoformat(d):
    """Return an ISO8601 date string that includes a timezone."""

    return d.replace(tzinfo=UTC()).isoformat()


def isoparse(s):
    """Parse an ISO8601 date string into a datetime object."""

    if not s:
        return None

    try:
        since = dateutil.parser.parse(s)
        utc_since = since.astimezone(UTC()).replace(tzinfo=None)
    except ValueError:
        raise BadRequest('Invalid changes-since parameter.')

    now = datetime.datetime.now()
    if utc_since > now:
        raise BadRequest('changes-since value set in the future.')

    if now - utc_since > timedelta(seconds=settings.POLL_LIMIT):
        raise BadRequest('Too old changes-since value.')

    return utc_since


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
            raise VirtualMachine.DeletedError
        if non_suspended and vm.suspended:
            raise Forbidden("Administratively Suspended VM")
        return vm
    except ValueError:
        raise BadRequest('Invalid server ID.')
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound('Server not found.')


def get_vm_meta(vm, key):
    """Return a VirtualMachineMetadata instance or raise ItemNotFound."""

    try:
        return VirtualMachineMetadata.objects.get(meta_key=key, vm=vm)
    except VirtualMachineMetadata.DoesNotExist:
        raise ItemNotFound('Metadata key not found.')


def get_image(image_id, user_id):
    """Return an Image instance or raise ItemNotFound."""

    backend = ImageBackend(user_id)
    try:
        image = backend.get_image(image_id)
        if not image:
            raise ItemNotFound('Image not found.')
        return image
    finally:
        backend.close()


def get_image_dict(image_id, user_id):
    image = {}
    img = get_image(image_id, user_id)
    properties = img.get('properties', {})
    image['backend_id'] = img['location']
    image['format'] = img['disk_format']
    image['metadata'] = dict((key.upper(), val) \
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
        raise ItemNotFound('Flavor not found.')


def get_network(network_id, user_id, for_update=False):
    """Return a Network instance or raise ItemNotFound."""

    try:
        network_id = int(network_id)
        objects = Network.objects
        if for_update:
            objects = objects.select_for_update()
        return objects.get(Q(userid=user_id) | Q(public=True), id=network_id)
    except (ValueError, Network.DoesNotExist):
        raise ItemNotFound('Network not found.')


def validate_network_size(cidr_block):
    """Return True if network size is allowed."""
    return cidr_block <= 29 and cidr_block > MAX_CIDR_BLOCK


def allocate_public_address(backend):
    """Allocate a public IP for a vm."""
    for network in backend_public_networks(backend):
        try:
            address = get_network_free_address(network)
            return (network, address)
        except EmptyPool:
            pass
    return (None, None)


def get_public_ip(backend):
    """Reserve an IP from a public network.

    This method should run inside a transaction.

    """
    address = None
    if settings.PUBLIC_USE_POOL:
        (network, address) = allocate_public_address(backend)
    else:
        for net in list(backend_public_networks(backend)):
            pool = net.get_pool()
            if not pool.empty():
                address = 'pool'
                network = net
                break
    if address is None:
        log.error("Public networks of backend %s are full", backend)
        raise OverLimit("Can not allocate IP for new machine."
                        " Public networks are full.")
    return (network, address)


def backend_public_networks(backend):
    """Return available public networks of the backend.

    Iterator for non-deleted public networks that are available
    to the specified backend.

    """
    for network in Network.objects.filter(public=True, deleted=False):
        if BackendNetwork.objects.filter(network=network,
                                         backend=backend).exists():
            yield network


def get_network_free_address(network):
    """Reserve an IP address from the IP Pool of the network.

    Raises EmptyPool

    """

    pool = network.get_pool()
    address = pool.get()
    pool.save()
    return address


def get_nic(machine, network):
    try:
        return NetworkInterface.objects.get(machine=machine, network=network)
    except NetworkInterface.DoesNotExist:
        raise ItemNotFound('Server not connected to this network.')


def get_nic_from_index(vm, nic_index):
    """Returns the nic_index-th nic of a vm
       Error Response Codes: itemNotFound (404), badMediaType (415)
    """
    matching_nics = vm.nics.filter(index=nic_index)
    matching_nics_len = len(matching_nics)
    if matching_nics_len < 1:
        raise  ItemNotFound('NIC not found on VM')
    elif matching_nics_len > 1:
        raise BadMediaType('NIC index conflict on VM')
    nic = matching_nics[0]
    return nic


def get_request_dict(request):
    """Returns data sent by the client as a python dict."""

    data = request.raw_post_data
    if request.META.get('CONTENT_TYPE').startswith('application/json'):
        try:
            return json.loads(data)
        except ValueError:
            raise BadRequest('Invalid JSON data.')
    else:
        raise BadRequest('Unsupported Content-Type.')


def update_response_headers(request, response):
    if request.serialization == 'xml':
        response['Content-Type'] = 'application/xml'
    elif request.serialization == 'atom':
        response['Content-Type'] = 'application/atom+xml'
    else:
        response['Content-Type'] = 'application/json'

    if settings.TEST:
        response['Date'] = format_date_time(time())

    add_never_cache_headers(response)


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
        data = render_to_string('meta.xml', dict(key=key, val=val))
    else:
        data = json.dumps(dict(meta=meta))
    return HttpResponse(data, status=status)


def render_fault(request, fault):
    if settings.DEBUG or settings.TEST:
        fault.details = format_exc(fault)

    if request.serialization == 'xml':
        data = render_to_string('fault.xml', {'fault': fault})
    else:
        d = {fault.name: {
                'code': fault.code,
                'message': fault.message,
                'details': fault.details}}
        data = json.dumps(d)

    resp = HttpResponse(data, status=fault.code)
    update_response_headers(request, resp)
    return resp


def request_serialization(request, atom_allowed=False):
    """Return the serialization format requested.

    Valid formats are 'json', 'xml' and 'atom' if `atom_allowed` is True.
    """

    path = request.path

    if path.endswith('.json'):
        return 'json'
    elif path.endswith('.xml'):
        return 'xml'
    elif atom_allowed and path.endswith('.atom'):
        return 'atom'

    for item in request.META.get('HTTP_ACCEPT', '').split(','):
        accept, sep, rest = item.strip().partition(';')
        if accept == 'application/json':
            return 'json'
        elif accept == 'application/xml':
            return 'xml'
        elif atom_allowed and accept == 'application/atom+xml':
            return 'atom'

    return 'json'


def api_method(http_method=None, atom_allowed=False):
    """Decorator function for views that implement an API method."""

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                request.serialization = request_serialization(request,
                                                              atom_allowed)
                get_user(request, settings.ASTAKOS_URL)
                if not request.user_uniq:
                    raise Unauthorized('No user found.')
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')

                resp = func(request, *args, **kwargs)
                update_response_headers(request, resp)
                return resp
            except VirtualMachine.DeletedError:
                fault = BadRequest('Server has been deleted.')
                return render_fault(request, fault)
            except Network.DeletedError:
                fault = BadRequest('Network has been deleted.')
                return render_fault(request, fault)
            except VirtualMachine.BuildingError:
                fault = BuildInProgress('Server is being built.')
                return render_fault(request, fault)
            except NotAllowedError:
                # Image Backend Unathorized
                fault = Forbidden('Request not allowed.')
                return render_fault(request, fault)
            except Fault, fault:
                if fault.code >= 500:
                    log.exception('API fault')
                return render_fault(request, fault)
            except BaseException:
                log.exception('Unexpected error')
                fault = ServiceUnavailable('Unexpected error.')
                return render_fault(request, fault)
        return wrapper
    return decorator


def construct_nic_id(nic):
    return "-".join(["nic", unicode(nic.machine.id), unicode(nic.index)])


def verify_personality(personality):
    """Verify that a a list of personalities is well formed"""
    if len(personality) > settings.MAX_PERSONALITY:
        raise OverLimit("Maximum number of personalities"
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
                raise OverLimit("Maximum size of personality exceeded")
            if len(b64decode(contents)) > settings.MAX_PERSONALITY_SIZE:
                raise OverLimit("Maximum size of personality exceeded")
        except AssertionError:
            raise BadRequest("Malformed personality in request")


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

def values_from_flavor(flavor):
    """Get Ganeti connectivity info from flavor type.

    If link or mac_prefix equals to "pool", then the resources
    are allocated from the corresponding Pools.

    """
    try:
        flavor = Network.FLAVORS[flavor]
    except KeyError:
        raise BadRequest("Unknown network flavor")

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
    from synnefo.ui.userdata.models import PublicKeyPair
    from synnefo.db.models import VirtualMachine, Network

    keypairusernames = PublicKeyPair.objects.filter().values_list('user',
                                                               flat=True)
    serverusernames = VirtualMachine.objects.filter().values_list('userid',
                                                                   flat=True)
    networkusernames = Network.objects.filter().values_list('userid',
                                                            flat=True)

    return set(list(keypairusernames) + list(serverusernames) + \
           list(networkusernames))


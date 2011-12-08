# Copyright 2011 GRNET S.A. All rights reserved.
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
import dateutil.parser

from base64 import b64encode
from datetime import timedelta, tzinfo
from functools import wraps
from hashlib import sha256
from random import choice
from string import ascii_letters, digits
from time import time
from traceback import format_exc
from wsgiref.handlers import format_date_time

from Crypto.Cipher import AES

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json
from django.utils.cache import add_never_cache_headers

from synnefo.api.faults import (Fault, BadRequest, BuildInProgress,
                                ItemNotFound, ServiceUnavailable, Unauthorized)
from synnefo.db.models import (Flavor, Image, ImageMetadata,
                                VirtualMachine, VirtualMachineMetadata,
                                Network, NetworkInterface)
from synnefo.plankton.backend import ImageBackend
from synnefo.util.log import getLogger


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

def random_password(length=8):
    pool = ascii_letters + digits
    return ''.join(choice(pool) for i in range(length))

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


def get_vm(server_id, owner):
    """Return a VirtualMachine instance or raise ItemNotFound."""

    try:
        server_id = int(server_id)
        return VirtualMachine.objects.get(id=server_id, owner=owner)
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

def get_image(image_id, owner):
    """Return an Image instance or raise ItemNotFound."""

    try:
        image_id = int(image_id)
        image = Image.objects.get(id=image_id)
        if not image.public and image.owner != owner:
            raise ItemNotFound('Image not found.')
        return image
    except ValueError:
        raise ItemNotFound('Image not found.')
    except Image.DoesNotExist:
        raise ItemNotFound('Image not found.')

def get_backend_image(image_id, owner):
    backend = ImageBackend(owner.uniq)
    try:
        image = backend.get_meta(image_id)
        if not image:
            raise ItemNotFound('Image not found.')
        return image
    finally:
        backend.close()

def get_image_meta(image, key):
    """Return a ImageMetadata instance or raise ItemNotFound."""

    try:
        return ImageMetadata.objects.get(meta_key=key, image=image)
    except ImageMetadata.DoesNotExist:
        raise ItemNotFound('Metadata key not found.')

def get_flavor(flavor_id):
    """Return a Flavor instance or raise ItemNotFound."""

    try:
        flavor_id = int(flavor_id)
        return Flavor.objects.get(id=flavor_id)
    except ValueError:
        raise BadRequest('Invalid flavor ID.')
    except Flavor.DoesNotExist:
        raise ItemNotFound('Flavor not found.')

def get_network(network_id, owner):
    """Return a Network instance or raise ItemNotFound."""

    try:
        if network_id == 'public':
            return Network.objects.get(public=True)
        else:
            network_id = int(network_id)
            return Network.objects.get(id=network_id, owner=owner)
    except ValueError:
        raise BadRequest('Invalid network ID.')
    except Network.DoesNotExist:
        raise ItemNotFound('Network not found.')

def get_nic(machine, network):
    try:
        return NetworkInterface.objects.get(machine=machine, network=network)
    except NetworkInterface.DoesNotExist:
        raise ItemNotFound('Server not connected to this network.')


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
        data = render_to_string('meta.xml', {'meta': meta})
    else:
        data = json.dumps({'meta': {meta.meta_key: meta.meta_value}})
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
            u = request.user.uniq if request.user else ''
            try:

                request.serialization = request_serialization(
                    request,
                    atom_allowed)
                if not request.method == 'GET':
                    if 'readonly' in request.__dict__ and \
                       request.readonly == True:
                        raise BadRequest('Method not allowed')
                if not request.user:
                    raise Unauthorized('No user found.')
                if http_method and request.method != http_method:
                    raise BadRequest('Method not allowed.')

                resp = func(request, *args, **kwargs)
                update_response_headers(request, resp)
                return resp
            except VirtualMachine.DeletedError:
                fault = BadRequest('Server has been deleted.')
                return render_fault(request, fault)
            except VirtualMachine.BuildingError:
                fault = BuildInProgress('Server is being built.')
                return render_fault(request, fault)
            except Fault, fault:
                return render_fault(request, fault)
            except BaseException, e:
                log.exception('Unexpected error')
                fault = ServiceUnavailable('Unexpected error.')
                return render_fault(request, fault)
        return wrapper
    return decorator

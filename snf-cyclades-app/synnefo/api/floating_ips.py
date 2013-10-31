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

from django.conf.urls.defaults import patterns
from django.db import transaction
from django.http import HttpResponse
from django.utils import simplejson as json

from snf_django.lib import api
from snf_django.lib.api import faults, utils
from synnefo.api import util
from synnefo import quotas
from synnefo.db.models import Network, IPAddress

from logging import getLogger
log = getLogger(__name__)

'''
ips_urlpatterns = patterns(
    'synnefo.api.floating_ips',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/(\w+)(?:.json|.xml)?$', 'floating_ip_demux'),
)

pools_urlpatterns = patterns(
    "synnefo.api.floating_ips",
    (r'^(?:/|.json|.xml)?$', 'list_floating_ip_pools'),
)
'''

ips_urlpatterns = patterns(
    'synnefo.api.floating_ips',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_floating_ips', {'detail': True}),
    (r'^/(\w+)(?:/|.json|.xml)?$', 'floating_ip_demux'))


def demux(request):
    if request.method == 'GET':
        return list_floating_ips(request)
    elif request.method == 'POST':
        return allocate_floating_ip(request)
    else:
        return api.api_method_not_allowed(request)


def floating_ip_demux(request, floating_ip_id):
    if request.method == 'GET':
        return get_floating_ip(request, floating_ip_id)
    elif request.method == 'DELETE':
        return release_floating_ip(request, floating_ip_id)
    elif request.method == 'PUT':
        return update_floating_ip(request, floating_ip_id)
    else:
        return api.api_method_not_allowed(request)


def ip_to_dict(floating_ip):
    machine_id = None
    port_id = None
    if floating_ip.nic is not None:
        machine_id = floating_ip.nic.machine_id
        port_id = floating_ip.nic.id
    return {"fixed_ip_address": None,
            "id": str(floating_ip.id),
            "instance_id": str(machine_id) if machine_id else None,
            "floating_ip_address": floating_ip.address,
            "port_id": str(floating_ip.nic.id) if port_id else None,
            "floating_network_id": str(floating_ip.network_id)}


@api.api_method(http_method="GET", user_required=True, logger=log,
                serializations=["json"])
def list_floating_ips(request):
    """Return user reserved floating IPs"""
    log.debug("list_floating_ips")

    userid = request.user_uniq
    floating_ips = IPAddress.objects.filter(userid=userid, deleted=False,
                                            floating_ip=True).order_by("id")\
                                    .select_related("nic")
    floating_ips = utils.filter_modified_since(request, objects=floating_ips)

    floating_ips = map(ip_to_dict, floating_ips)

    request.serialization = "json"
    data = json.dumps({"floatingips": floating_ips})

    return HttpResponse(data, status=200)


@api.api_method(http_method="GET", user_required=True, logger=log,
                serializations=["json"])
def get_floating_ip(request, floating_ip_id):
    """Return information for a floating IP."""
    userid = request.user_uniq
    floating_ip = util.get_floating_ip_by_id(userid, floating_ip_id)
    request.serialization = "json"
    data = json.dumps({"floatingip": ip_to_dict(floating_ip)})
    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def allocate_floating_ip(request):
    """Allocate a floating IP."""
    req = utils.get_request_dict(request)
    floating_ip_dict = api.utils.get_attribute(req, "floatingip",
                                               required=True)
    log.info('allocate_floating_ip %s', req)

    userid = request.user_uniq

    # the network_pool is a mandatory field
    network_id = api.utils.get_attribute(floating_ip_dict,
                                         "floating_network_id",
                                         required=False)
    if network_id is None:
        floating_ip = util.allocate_public_ip(userid, floating_ip=True)
    else:
        try:
            network_id = int(network_id)
        except ValueError:
            raise faults.BadRequest("Invalid networkd ID.")

        network = util.get_network(network_id, userid, for_update=True,
                                   non_deleted=True)
        if not network.floating_ip_pool:
            # TODO: Maybe 409 ??
            # Check that it is a floating IP pool
            raise faults.ItemNotFound("Floating IP pool %s does not exist." %
                                      network_id)

        address = api.utils.get_attribute(floating_ip_dict,
                                          "floating_ip_address",
                                          required=False)

        # Allocate the floating IP
        floating_ip = util.allocate_ip(network, userid, address=address,
                                       floating_ip=True)

    # Issue commission (quotas)
    quotas.issue_and_accept_commission(floating_ip)
    transaction.commit()

    log.info("User '%s' allocated floating IP '%s'", userid, floating_ip)

    request.serialization = "json"
    data = json.dumps({"floatingip": ip_to_dict(floating_ip)})
    return HttpResponse(data, status=200)


@api.api_method(http_method='DELETE', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def release_floating_ip(request, floating_ip_id):
    """Release a floating IP."""
    userid = request.user_uniq
    log.info("release_floating_ip '%s'. User '%s'.", floating_ip_id, userid)

    floating_ip = util.get_floating_ip_by_id(userid, floating_ip_id,
                                             for_update=True)
    if floating_ip.nic:
        # This is safe, you also need for_update to attach floating IP to
        # instance.
        msg = "Floating IP '%s' is attached to instance." % floating_ip.id
        raise faults.Conflict(msg)

    # Return the address of the floating IP back to pool
    floating_ip.release_address()
    # And mark the floating IP as deleted
    floating_ip.deleted = True
    floating_ip.save()
    # Release quota for floating IP
    quotas.issue_and_accept_commission(floating_ip, delete=True)
    transaction.commit()
    # Delete the floating IP from DB
    floating_ip.delete()

    log.info("User '%s' released IP '%s", userid, floating_ip)

    return HttpResponse(status=204)


@api.api_method(http_method='PUT', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def update_floating_ip(request, floating_ip_id):
    """Update a floating IP."""
    raise faults.NotImplemented("Updating a floating IP is not supported.")
    #userid = request.user_uniq
    #log.info("update_floating_ip '%s'. User '%s'.", floating_ip_id, userid)

    #req = utils.get_request_dict(request)
    #info = api.utils.get_attribute(req, "floatingip", required=True)

    #device_id = api.utils.get_attribute(info, "device_id", required=False)

    #floating_ip = util.get_floating_ip_by_id(userid, floating_ip_id,
    #                                         for_update=True)
    #if device_id:
    #    # attach
    #    vm = util.get_vm(device_id, userid)
    #    nic, floating_ip = servers.create_nic(vm, ipaddress=floating_ip)
    #    backend.connect_to_network(vm, nic)
    #else:
    #    # dettach
    #    nic = floating_ip.nic
    #    if not nic:
    #        raise faults.BadRequest("The floating IP is not associated\
    #                                with any device")
    #    vm = nic.machine
    #    servers.disconnect(vm, nic)
    #return HttpResponse(status=202)


# Floating IP pools
@api.api_method(http_method='GET', user_required=True, logger=log,
                serializations=["json"])
def list_floating_ip_pools(request):
    networks = Network.objects.filter(public=True, floating_ip_pool=True,
                                      deleted=False)
    networks = utils.filter_modified_since(request, objects=networks)
    floating_ip_pools = map(network_to_floating_ip_pool, networks)
    request.serialization = "json"
    data = json.dumps({"floating_ip_pools": floating_ip_pools})
    request.serialization = "json"
    return HttpResponse(data, status=200)


def network_to_floating_ip_pool(network):
    """Convert a 'Network' object to a floating IP pool dict."""
    total, free = network.ip_count()
    return {"name": str(network.id),
            "size": total,
            "free": free}

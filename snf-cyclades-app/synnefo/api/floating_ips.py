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
from synnefo.db.models import Network, FloatingIP


from logging import getLogger
log = getLogger(__name__)

ips_urlpatterns = patterns(
    'synnefo.api.floating_ips',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/(\w+)(?:.json|.xml)?$', 'floating_ip_demux'),
)

pools_urlpatterns = patterns(
    "synnefo.api.floating_ips",
    (r'^(?:/|.json|.xml)?$', 'list_floating_ip_pools'),
)


def demux(request):
    if request.method == 'GET':
        return list_floating_ips(request)
    elif request.method == 'POST':
        return allocate_floating_ip(request)
    else:
        return api.method_not_allowed(request)


def floating_ip_demux(request, floating_ip_id):
    if request.method == 'GET':
        return get_floating_ip(request, floating_ip_id)
    elif request.method == 'DELETE':
        return release_floating_ip(request, floating_ip_id)
    else:
        return api.method_not_allowed(request)


def ip_to_dict(floating_ip):
    machine_id = floating_ip.machine_id
    return {"fixed_ip": None,
            "id": str(floating_ip.id),
            "instance_id": str(machine_id) if machine_id else None,
            "ip": floating_ip.ipv4,
            "pool": str(floating_ip.network_id)}


@api.api_method(http_method="GET", user_required=True, logger=log)
def list_floating_ips(request):
    """Return user reserved floating IPs"""
    log.debug("list_floating_ips")

    userid = request.user_uniq
    floating_ips = FloatingIP.objects.filter(userid=userid, deleted=False)\
                                     .order_by("id")

    floating_ips = map(ip_to_dict, floating_ips)

    request.serialization = "json"
    data = json.dumps({"floating_ips": floating_ips})

    return HttpResponse(data, status=200)


@api.api_method(http_method="GET", user_required=True, logger=log)
def get_floating_ip(request, floating_ip_id):
    """Return information for a floating IP."""
    userid = request.user_uniq
    try:
        floating_ip = FloatingIP.objects.get(id=floating_ip_id,
                                             deleted=False,
                                             userid=userid)
    except FloatingIP.DoesNotExist:
        raise faults.ItemNotFound("Floating IP '%s' does not exist" %
                                  floating_ip_id)
    request.serialization = "json"
    data = json.dumps({"floating_ip": ip_to_dict(floating_ip)})
    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
@transaction.commit_manually
def allocate_floating_ip(request):
    """Allocate a floating IP."""
    req = utils.get_request_dict(request)
    log.info('allocate_floating_ip %s', req)

    userid = request.user_uniq
    pool = req.get("pool", None)
    address = req.get("address", None)
    machine = None
    net_objects = Network.objects.select_for_update()\
                                 .filter(public=True, floating_ip_pool=True,
                                         deleted=False)
    try:
        if pool is None:
            # User did not specified a pool. Choose a random public IP
            network, address = util.allocate_public_ip(net_objects)
        else:
            try:
                network = Network.objects.select_for_update()\
                                         .get(id=pool, public=True,
                                              deleted=False,
                                              floating_ip_pool=True)

            except IndexError:
                raise faults.ItemNotFound("Pool '%s' does not exist." % pool)
            if address is None:
                # User did not specified an IP address. Choose a random one
                # Gets X-Lock on IP pool
                address = util.get_network_free_address(network)
            else:
                # User specified an IP address. Check that it is not a used
                # floating IP
                if FloatingIP.objects.filter(network=network,
                                             deleted=False,
                                             ipv4=address).exists():
                    msg = "Floating IP '%s' is reserved" % address
                    raise faults.Conflict(msg)
                pool = network.get_pool()  # Gets X-Lock
                # Check address belongs to pool
                if not pool.contains(address):
                    raise faults.BadRequest("Invalid address")
                if pool.is_available(address):
                    pool.reserve(address)
                    pool.save()
                # If address is not available, check that it belongs to the
                # same user
                elif not network.nics.filter(ipv4=address,
                                            machine__userid=userid).exists():
                        msg = "Address '%s' is already in use" % address
                        raise faults.Conflict(msg)
        floating_ip = FloatingIP.objects.create(ipv4=address, network=network,
                                                userid=userid, machine=machine)
        quotas.issue_and_accept_commission(floating_ip)
    except:
        transaction.rollback()
        raise
    else:
        transaction.commit()

    log.info("User '%s' allocated floating IP '%s", userid, floating_ip)

    request.serialization = "json"
    data = json.dumps({"floating_ip": ip_to_dict(floating_ip)})
    return HttpResponse(data, status=200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def release_floating_ip(request, floating_ip_id):
    """Release a floating IP."""
    userid = request.user_uniq
    log.info("release_floating_ip '%s'. User '%s'.", floating_ip_id, userid)
    try:
        floating_ip = FloatingIP.objects.select_for_update()\
                                        .get(id=floating_ip_id,
                                             deleted=False,
                                             userid=userid)
    except FloatingIP.DoesNotExist:
        raise faults.ItemNotFound("Floating IP '%s' does not exist" %
                                  floating_ip_id)

    # Since we have got an exlusively lock in floating IP, and since
    # to remove a floating IP you need the same lock, the in_use() query
    # is safe
    if floating_ip.in_use():
        msg = "Floating IP '%s' is used" % floating_ip.id
        raise faults.Conflict(message=msg)

    try:
        floating_ip.network.release_address(floating_ip.ipv4)
        floating_ip.deleted = True
        quotas.issue_and_accept_commission(floating_ip, delete=True)
    except:
        transaction.rollback()
        raise
    else:
        floating_ip.delete()
        transaction.commit()

    log.info("User '%s' released IP '%s", userid, floating_ip)

    return HttpResponse(status=204)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_floating_ip_pools(request):
    networks = Network.objects.filter(public=True, deleted=False,
                                      floating_ip_pool=True)
    pools = [{"name": str(net.id)} for net in networks]
    request.serialization = "json"
    data = json.dumps({"floating_ip_pools": pools})
    request.serialization = "json"
    return HttpResponse(data, status=200)

# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from django.http import HttpResponse
from django.conf.urls import patterns
from django.utils import simplejson as json
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from snf_django.lib import api
from snf_django.lib.api import utils
from django.template.loader import render_to_string
from synnefo.api import util

from synnefo.db.models import VirtualMachine, IPAddress, NetworkInterface
from logging import getLogger

from synnefo.logic import servers, backend

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.routers',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_routers', {'detail': True}),
    (r'^/([-\w]+)(?:/|.json|.xml)?$', 'router_demux'),
    (r'^/([-\w]+)/(remove_router_interface|add_router_interface)$',
        'rinterface_demux'))


def demux(request):
    if request.method == 'GET':
        return list_routers(request)
    elif request.method == 'POST':
        return create_router(request)
    else:
        return api.api_method_not_allowed(request)


def router_demux(request, offset):
    if request.method == 'GET':
        return get_router(request,  offset)
    elif request.method == 'DELETE':
        return delete_router(request, offset)
    elif request.method == 'PUT':
        return update_router(request, offset)
    else:
        return api.api_method_not_allowed(request)


def rinterface_demux(request, router_id, command):
    if request.method == 'PUT':
        if command == "add_router_interface":
            return add_interface(request, router_id)
        elif command == "remove_router_interface":
            return remove_interface(request, router_id)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_routers(request, detail=False):
    log.debug('list_routers')

    user_routers = VirtualMachine.objects.filter(userid=request.user_uniq,
                                                 router=True)

    user_routers = utils.filter_modified_since(request, objects=user_routers)

    routers = [router_to_dict(router, detail)
               for router in user_routers.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_routers.xml', {
            'routers': routers})
    else:
        data = json.dumps({"routers": routers})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def create_router(request):
    user_id = request.user_uniq
    req = utils.get_request_dict(request)

    info = api.utils.get_attribute(req, 'router', required=True)
    gateway_info = api.utils.get_attribute(info, 'external_gateway_info',
                                            required=True)
    net_id = api.utils.get_attribute(gateway_info, 'network_id', required=True)

    #find the network
    network = util.get_network(net_id, request.user_uniq)

    fip_address = api.utils.get_attribute(gateway_info, 'floating_ip',
                                          required=False)
    if fip_address:
        #find the floating ip
        floating_ip = util.get_floating_ip_by_address(user_id, fip_address,
                                                      for_update=True)
        if floating_ip.network.id != network.id:
            msg = "The ip is not on the given network"
            raise api.faults.Conflict(msg)
    else:
        #assuming that the floating-ips are preallocated
        fips = IPAddress.objects.filter(userid=user_id,
                                               network=network,
                                               nic=None,
                                               floating_ip=True)
        if fips:
            floating_ip = fips[0]
        else:
            # FIXME return correct code
            raise api.faults.BadRequest('No available floating ips')

    name = api.utils.get_attribute(info, 'name', required=False)
    if not name:
        name = 'random-router'

    #FIXME : double query for floating-ip
    #create the router
    vm = servers.create(user_id,
                        name,
                        'password',
                        'flavor',
                        'image',
                        floating_ips=[floating_ip.address])

    response = render_router(request, router_to_dict(vm, detail=True),
                             status=201)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_router(request, router_id):
    log.debug('get_router_details %s', router_id)
    router = util.get_vm(router_id, request.user_uniq)

    router_dict = router_to_dict(router, detail=True)
    return render_router(request, router_dict)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
def delete_router(request, router_id):
    log.debug('delete router  %s', router_id)
    router = util.get_vm(router_id, request.user_uniq)

    if router.networks.filter(external_router=False):
        return HttpResponse("There are internal interfaces on the router",
                            status=409)

    servers.destroy(router)

    return HttpResponse(status=204)


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_router(request, router_id):
    """ Update only name and external_gateway_info"""

    log.debug('update router %s', router_id)
    router = util.get_vm(router_id, request.user_uniq)
    user_id = request.user_uniq
    req = utils.get_request_dict(request)

    info = api.utils.get_attribute(req, 'router', required=True)
    gateway = api.utils.get_attribute(info, 'external_gateway_info',
                                      required=False)
    if gateway:
        net_id = api.utils.get_attribute(gateway, 'network_id', required=True)
        fip_address = api.utils.get_attribute(gateway, 'floating_ip',
                                              required=False)

    # rename if name given
    name = api.utils.get_attribute(info, 'name', required=False)
    if name:
        servers.rename(router, name)

    if gateway:
        #find the new network
        network = util.get_network(net_id, request.user_uniq)

        if fip_address:
            #find the floating ip
            floating_ip = util.get_floating_ip_by_address(user_id, fip_address,
                                                          for_update=True)
            if floating_ip.network.id != network.id:
                msg = "The ip is not on the given network"
                raise api.faults.Conflict(msg)
        else:
            #assuming that the floating-ips are preallocated
            fips = IPAddress.objects.filter(userid=user_id,
                                                   network=network,
                                                   nic=None,
                                                   floating_ip=True)
            if fips:
                floating_ip = fips[0]
            else:
                # FIXME return correct code
                raise api.faults.BadRequest('No available floating ips')

        #disconnect from the old net if any
        try:
            old_nic = router.nics.get(network__external_router=True)
        except NetworkInterface.DoesNotExist:
            old_nic = None

        if old_nic:
                servers.disconnect(router, old_nic)

        #add the new floating-ip
        servers.create_nic(router, ipaddress=floating_ip)

    routerdict = router_to_dict(router)
    return render_router(request, routerdict, 200)


@api.api_method(http_method='PUT', user_required=True, logger=log)
def add_interface(request, router_id):
    log.debug('add interface to router %s', router_id)
    info = utils.get_request_dict(request)
    router = util.get_vm(router_id, request.user_uniq)

    subnet_id = api.utils.get_attribute(info, "subnet_id", required=True)
    subnet = util.get_subnet(subnet_id, request.user_uniq, public=False)

    if subnet.ipversion != 4:
        raise api.faults.BadRequest("IPv4 subnet needed")

    #create nic
    nic, ippaddress = servers.create_nic(router, subnet.network,
                                         address=subnet.gateway)
    #connect
    backend.connect(router, nic)

    res = {"port_id": str(nic.id),
           "subnet_id": subnet.id}

    data = json.dumps(res)
    return HttpResponse(data, status=200)


@api.api_method(http_method='PUT', user_required=True, logger=log)
def remove_interface(request, router_id):

    log.debug('remove interface from router %s', router_id)

    router = util.get_vm(router_id, request.user_uniq)

    info = utils.get_request_dict(request)

    subnet_id = api.utils.get_attribute(info, "subnet_id", required=True)
    subnet = util.get_subnet(subnet_id, request.user_uniq, public=False)

    #get the port
    try:
        port = router.nics.get(network=subnet)
    except (ValueError, NetworkInterface.DoesNotExist):
        raise api.faults.ItemNotFound('Port not found')

    res = {"id": str(router.id),
           "tenant_id": request.user_uniq,
           "port_id": str(port.id),
           "subnet_id": str(subnet.id)}

    #disconnect
    servers.disconnect(router, port)

    data = json.dumps(res)
    return HttpResponse(data, status=200)


# util functions


def router_to_dict(router, detail=True):
    d = {'id': str(router.id), 'name': router.name}
    d['user_id'] = router.userid
    d['tenant_id'] = router.userid
    d['admin_state_up'] = True
    if detail:
        external_nic = router.nics.get(network__external_router=True)
        if external_nic:
            fip = external_nic.ips.get(floating_ip=True)
            d['external_gateway_info'] = {'network_id':
                                            str(external_nic.network.id),
                                          'floating_ip_id': fip.address}
        else:
            d['external_gateway_info'] = None
    return d


def render_router(request, routerdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('router.xml', {'router': routerdict})
    else:
        data = json.dumps({'router': routerdict})
    return HttpResponse(data, status=status)


# mock functions

def mock_disconnect(router, net):
    nic = models.NetworkInterface.objects.get(network=net, machine=router)
    nic.delete()


def mock_connect(router, net, fip):
    fip.machine = router
    nic = models.NetworkInterface.objects.create(network=net,
                                                 machine=router,
                                                 ipv4=fip.ipv4,
                                                 owner="router")
    nic.save()
    fip.save()

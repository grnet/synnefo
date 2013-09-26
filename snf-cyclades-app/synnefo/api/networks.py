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


from django.conf import settings
try:
    from django.conf.urls import patterns
except ImportError:  # Django==1.2
    from django.conf.urls.defaults import patterns

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from snf_django.lib import api
from snf_django.lib.api import faults, utils
from synnefo.api import util
from synnefo.api.actions import network_actions
from synnefo import quotas
from synnefo.db.models import Network
from synnefo.db.utils import validate_mac
from synnefo.db.pools import EmptyPool
from synnefo.logic import backend


from logging import getLogger
log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.networks',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_networks', {'detail': True}),
    (r'^/(\w+)(?:.json|.xml)?$', 'network_demux'),
    (r'^/(\w+)/action(?:.json|.xml)?$', 'network_action'),
)


def demux(request):
    if request.method == 'GET':
        return list_networks(request)
    elif request.method == 'POST':
        return create_network(request)
    else:
        return api.api_method_not_allowed(request)


def network_demux(request, network_id):
    if request.method == 'GET':
        return get_network_details(request, network_id)
    elif request.method == 'PUT':
        return update_network_name(request, network_id)
    elif request.method == 'DELETE':
        return delete_network(request, network_id)
    else:
        return api.api_method_not_allowed(request)


def network_to_dict(network, user_id, detail=True):
    d = {'id': str(network.id), 'name': network.name}
    d['links'] = util.network_to_links(network.id)
    if detail:
        d['user_id'] = network.userid
        d['tenant_id'] = network.userid
        d['cidr'] = network.subnet
        d['cidr6'] = network.subnet6
        d['gateway'] = network.gateway
        d['gateway6'] = network.gateway6
        d['dhcp'] = network.dhcp
        d['type'] = network.flavor
        d['updated'] = utils.isoformat(network.updated)
        d['created'] = utils.isoformat(network.created)
        d['status'] = network.state
        d['public'] = network.public

        attachments = [util.construct_nic_id(nic)
                       for nic in network.nics.filter(machine__userid=user_id)
                                              .filter(state="ACTIVE")
                                              .order_by('machine')]
        d['attachments'] = attachments
    return d


def render_network(request, networkdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'network': networkdict})
    else:
        data = json.dumps({'network': networkdict})
    return HttpResponse(data, status=status)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_networks(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_networks detail=%s', detail)
    since = utils.isoparse(request.GET.get('changes-since'))
    user_networks = Network.objects.filter(Q(userid=request.user_uniq) |
                                           Q(public=True))

    if since:
        user_networks = user_networks.filter(updated__gte=since)
        if not user_networks:
            return HttpResponse(status=304)
    else:
        user_networks = user_networks.filter(deleted=False)

    networks = [network_to_dict(network, request.user_uniq, detail)
                for network in user_networks.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {
            'networks': networks,
            'detail': detail})
    else:
        data = json.dumps({'networks': networks})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
@transaction.commit_on_success
def create_network(request):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badMediaType(415),
    #                       badRequest (400),
    #                       forbidden (403)
    #                       overLimit (413)

    req = utils.get_request_dict(request)
    log.info('create_network %s', req)

    user_id = request.user_uniq
    try:
        d = req['network']
        name = d['name']
    except KeyError:
        raise faults.BadRequest("Malformed request")

    # Get and validate flavor. Flavors are still exposed as 'type' in the
    # API.
    flavor = d.get("type", None)
    if flavor is None:
        raise faults.BadRequest("Missing request parameter 'type'")
    elif flavor not in Network.FLAVORS.keys():
        raise faults.BadRequest("Invalid network type '%s'" % flavor)
    elif flavor not in settings.API_ENABLED_NETWORK_FLAVORS:
        raise faults.Forbidden("Can not create network of type '%s'" %
                               flavor)

    public = d.get("public", False)
    if public:
        raise faults.Forbidden("Can not create a public network.")

    dhcp = d.get('dhcp', True)

    # Get and validate network parameters
    subnet = d.get('cidr', '192.168.1.0/24')
    subnet6 = d.get('cidr6', None)
    gateway = d.get('gateway', None)
    gateway6 = d.get('gateway6', None)
    # Check that user provided a valid subnet
    util.validate_network_params(subnet, gateway, subnet6, gateway6)

    try:
        mode, link, mac_prefix, tags = util.values_from_flavor(flavor)
        validate_mac(mac_prefix + "0:00:00:00")
        network = Network.objects.create(
            name=name,
            userid=user_id,
            subnet=subnet,
            subnet6=subnet6,
            gateway=gateway,
            gateway6=gateway6,
            dhcp=dhcp,
            flavor=flavor,
            mode=mode,
            link=link,
            mac_prefix=mac_prefix,
            tags=tags,
            action='CREATE',
            state='ACTIVE')
    except EmptyPool:
        log.error("Failed to allocate resources for network of type: %s",
                  flavor)
        raise faults.ServiceUnavailable("Failed to allocate network resources")

    # Issue commission to Quotaholder and accept it since at the end of
    # this transaction the Network object will be created in the DB.
    # Note: the following call does a commit!
    quotas.issue_and_accept_commission(network)

    networkdict = network_to_dict(network, request.user_uniq)
    response = render_network(request, networkdict, status=202)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_network_details(request, network_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.debug('get_network_details %s', network_id)
    net = util.get_network(network_id, request.user_uniq)
    netdict = network_to_dict(net, request.user_uniq)
    return render_network(request, netdict)


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_network_name(request, network_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       forbidden (403)
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    req = utils.get_request_dict(request)
    log.info('update_network_name %s', network_id)

    try:
        name = req['network']['name']
    except (TypeError, KeyError):
        raise faults.BadRequest('Malformed request.')

    net = util.get_network(network_id, request.user_uniq)
    if net.public:
        raise faults.Forbidden('Can not rename the public network.')
    if net.deleted:
        raise faults.BadRequest("Network has been deleted.")
    net.name = name
    net.save()
    return HttpResponse(status=204)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_network(request, network_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       forbidden (403)
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.info('delete_network %s', network_id)
    net = util.get_network(network_id, request.user_uniq, for_update=True)
    if net.public:
        raise faults.Forbidden('Can not delete the public network.')

    if net.deleted:
        raise faults.BadRequest("Network has been deleted.")

    if net.machines.all():  # Nics attached on network
        raise faults.NetworkInUse('Machines are connected to network.')

    net.action = 'DESTROY'
    net.save()

    backend_networks = net.backend_networks.exclude(operstate="DELETED")
    for bnet in backend_networks:
        backend.delete_network(net, bnet.backend)
    if not backend_networks:
        backend.update_network_state(net)
    return HttpResponse(status=204)


@api.api_method(http_method='POST', user_required=True, logger=log)
def network_action(request, network_id):
    req = utils.get_request_dict(request)
    log.debug('network_action %s %s', network_id, req)
    if len(req) != 1:
        raise faults.BadRequest('Malformed request.')

    net = util.get_network(network_id, request.user_uniq)
    if net.public:
        raise faults.Forbidden('Can not modify the public network.')
    if net.deleted:
        raise faults.BadRequest("Network has been deleted.")

    try:
        key = req.keys()[0]
        val = req[key]
        assert isinstance(val, dict)
        return network_actions[key](request, net, req[key])
    except KeyError:
        raise faults.BadRequest('Unknown action.')
    except AssertionError:
        raise faults.BadRequest('Invalid argument.')

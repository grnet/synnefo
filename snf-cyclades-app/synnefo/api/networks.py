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

from django.conf import settings
from django.conf.urls import patterns
from django.http import HttpResponse
from django.utils import simplejson as json
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string

from snf_django.lib import api

from synnefo.api import util
from synnefo.db.models import Network
from synnefo.logic import networks

from logging import getLogger

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.networks',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_networks', {'detail': True}),
    (r'^/(\w+)(?:/|.json|.xml)?$', 'network_demux'))


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
    elif request.method == 'DELETE':
        return delete_network(request, network_id)
    elif request.method == 'PUT':
        return update_network(request, network_id)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_networks(request, detail=False):
    log.debug('list_networks detail=%s', detail)

    user_networks = Network.objects.filter(Q(userid=request.user_uniq) |
                                           Q(public=True))\
                                   .prefetch_related("subnets")

    user_networks = api.utils.filter_modified_since(request,
                                                    objects=user_networks)

    network_dicts = [network_to_dict(network, detail)
                     for network in user_networks.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {
            "networks": network_dicts})
    else:
        data = json.dumps({'networks': network_dicts})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def create_network(request):
    userid = request.user_uniq
    req = api.utils.get_request_dict(request)
    log.info('create_network %s', req)

    network_dict = api.utils.get_attribute(req, "network")
    flavor = api.utils.get_attribute(network_dict, "type")

    if flavor not in Network.FLAVORS.keys():
        raise api.faults.BadRequest("Invalid network type '%s'" % flavor)
    if flavor not in settings.API_ENABLED_NETWORK_FLAVORS:
        raise api.faults.Forbidden("Can not create network of type '%s'." %
                                   flavor)

    name = api.utils.get_attribute(network_dict, "name", required=False)
    if name is None:
        name = ""

    network = networks.create(userid=userid, name=name, flavor=flavor,
                              public=False)
    networkdict = network_to_dict(network, detail=True)
    response = render_network(request, networkdict, status=201)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_network_details(request, network_id):
    log.debug('get_network_details %s', network_id)
    network = util.get_network(network_id, request.user_uniq)
    return render_network(request, network_to_dict(network, detail=True))


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_network(request, network_id):
    info = api.utils.get_request_dict(request)

    network = api.utils.get_attribute(info, "network", required=True)
    new_name = api.utils.get_attribute(network, "name")

    network = util.get_network(network_id, request.user_uniq, for_update=True)
    if network.public:
        raise api.faults.Forbidden("Can not rename the public network.")
    network = networks.rename(network, new_name)
    return render_network(request, network_to_dict(network), 200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_network(request, network_id):
    log.info('delete_network %s', network_id)
    network = util.get_network(network_id, request.user_uniq, for_update=True)
    if network.public:
        raise api.faults.Forbidden("Can not delete the public network.")
    networks.delete(network)
    return HttpResponse(status=204)


def network_to_dict(network, detail=True):
    d = {'id': str(network.id), 'name': network.name}
    d['links'] = util.network_to_links(network.id)
    if detail:
        d['user_id'] = network.userid
        d['tenant_id'] = network.userid
        d['type'] = network.flavor
        d['updated'] = api.utils.isoformat(network.updated)
        d['created'] = api.utils.isoformat(network.created)
        d['status'] = network.state
        d['public'] = network.public
        d['external_router'] = network.external_router
        d['admin_state_up'] = True
        d['subnets'] = list(network.subnets.values_list('id', flat=True))
        d['SNF:floating_ip_pool'] = network.floating_ip_pool
    return d


def render_network(request, networkdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'network': networkdict})
    else:
        data = json.dumps({'network': networkdict})
    return HttpResponse(data, status=status)

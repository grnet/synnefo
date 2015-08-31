# Copyright (C) 2010-2015 GRNET S.A. and individual contributors
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

from django.conf import settings
from django.conf.urls import patterns
from django.http import HttpResponse
from django.utils import simplejson as json
from synnefo.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string

from snf_django.lib import api
from snf_django.lib.api import utils

from synnefo.api import util
from synnefo.db.models import Network
from synnefo.logic import networks

from logging import getLogger

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.networks',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_networks', {'detail': True}),
    (r'^/(\w+)(?:/|.json|.xml)?$', 'network_demux'),
    (r'^/(\w+)/action(?:/|.json|.xml)?$', 'network_action_demux'),
)


def demux(request):
    if request.method == 'GET':
        return list_networks(request)
    elif request.method == 'POST':
        return create_network(request)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def network_demux(request, network_id):

    if request.method == 'GET':
        return get_network_details(request, network_id)
    elif request.method == 'DELETE':
        return delete_network(request, network_id)
    elif request.method == 'PUT':
        return update_network(request, network_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET',
                                                           'PUT',
                                                           'DELETE'])


@api.api_method(http_method='POST', user_required=True, logger=log)
def network_action_demux(request, network_id):
    req = utils.get_json_body(request)
    network = util.get_network(network_id, request.user_uniq, for_update=True,
                               non_deleted=True)
    action = req.keys()[0]
    try:
        f = NETWORK_ACTIONS[action]
    except KeyError:
        raise api.faults.BadRequest("Action %s not supported." % action)
    action_args = req[action]
    if not isinstance(action_args, dict):
        raise api.faults.BadRequest("Invalid argument.")

    return f(request, network, action_args)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_networks(request, detail=True):
    log.debug('list_networks detail=%s', detail)

    user_networks = Network.objects.filter(Q(userid=request.user_uniq) |
                                           Q(public=True))\
                                   .order_by('id')

    user_networks = api.utils.filter_modified_since(request,
                                                    objects=user_networks)

    network_dicts = [network_to_dict(network, detail)
                     for network in user_networks]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {
            "networks": network_dicts})
    else:
        data = json.dumps({'networks': network_dicts})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def create_network(request):
    userid = request.user_uniq
    req = api.utils.get_json_body(request)
    log.info('create_network user: %s request: %s', userid, req)

    network_dict = api.utils.get_attribute(req, "network",
                                           attr_type=dict)
    flavor = api.utils.get_attribute(network_dict, "type",
                                     attr_type=basestring)

    if flavor not in Network.FLAVORS.keys():
        raise api.faults.BadRequest("Invalid network type '%s'" % flavor)
    if flavor not in settings.API_ENABLED_NETWORK_FLAVORS:
        raise api.faults.Forbidden("Cannot create network of type '%s'." %
                                   flavor)

    name = api.utils.get_attribute(network_dict, "name", attr_type=basestring,
                                   required=False)
    if name is None:
        name = ""

    project = network_dict.get('project', None)
    network = networks.create(userid=userid, name=name, flavor=flavor,
                              public=False, project=project)
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
    info = api.utils.get_json_body(request)

    network = api.utils.get_attribute(info, "network", attr_type=dict,
                                      required=True)
    new_name = api.utils.get_attribute(network, "name", attr_type=basestring)

    network = util.get_network(network_id, request.user_uniq, for_update=True,
                               non_deleted=True)
    if network.public:
        raise api.faults.Forbidden("Cannot rename the public network.")
    network = networks.rename(network, new_name)
    return render_network(request, network_to_dict(network), 200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_network(request, network_id):
    log.info('delete_network %s', network_id)
    network = util.get_network(network_id, request.user_uniq, for_update=True,
                               non_deleted=True)
    if network.public:
        raise api.faults.Forbidden("Cannot delete the public network.")
    networks.delete(network)
    return HttpResponse(status=204)


def network_to_dict(network, detail=True):
    d = {'id': str(network.id), 'name': network.name}
    d['links'] = util.network_to_links(network.id)
    if detail:
        state = "SNF:DRAINED" if network.drained else network.state
        d['user_id'] = network.userid
        d['tenant_id'] = network.project
        d['shared_to_project'] = network.shared_to_project
        d['type'] = network.flavor
        d['updated'] = api.utils.isoformat(network.updated)
        d['created'] = api.utils.isoformat(network.created)
        d['status'] = state
        d['public'] = network.public
        d['shared'] = network.public
        d['router:external'] = network.external_router
        d['admin_state_up'] = True
        d['subnets'] = network.subnet_ids
        d['SNF:floating_ip_pool'] = network.floating_ip_pool
        d['deleted'] = network.deleted
    return d


@transaction.commit_on_success
def reassign_network(request, network, args):
    project = args.get("project")
    if project is None:
        raise api.faults.BadRequest("Missing 'project' attribute.")
    networks.reassign(network, project)
    return HttpResponse(status=200)


NETWORK_ACTIONS = {
    "reassign": reassign_network,
}


def render_network(request, networkdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'network': networkdict})
    else:
        data = json.dumps({'network': networkdict})
    return HttpResponse(data, status=status)

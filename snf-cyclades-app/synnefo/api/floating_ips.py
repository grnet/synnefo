# Copyright (C) 2010-2016 GRNET S.A. and individual contributors
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

from django.conf.urls import patterns
from synnefo.db import transaction
from django.conf import settings
from django.http import HttpResponse
import json

from snf_django.lib import api
from snf_django.lib.api import faults, utils
from synnefo.api import util
from synnefo.logic import ips
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


def compute_ip_to_dict(floating_ip):
    machine_id = None
    if floating_ip.nic is not None:
        machine_id = floating_ip.nic.machine_id
    return {"fixed_ip": None,
            "id": floating_ip.id,
            "instance_id": str(machine_id) if machine_id else None,
            "ip": floating_ip.address,
            "pool": None}


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
            "port_id": str(port_id) if port_id else None,
            "floating_network_id": str(floating_ip.network_id),
            "user_id": floating_ip.userid,
            "tenant_id": floating_ip.project,
            "shared_to_project": floating_ip.shared_to_project,
            "deleted": floating_ip.deleted}


def _floatingip_details_view(floating_ip):
    return json.dumps({'floatingip': ip_to_dict(floating_ip)})


def _floatingip_list_view(floating_ips):
    floating_ips = map(ip_to_dict, floating_ips)
    return json.dumps({'floatingips': floating_ips})


def _compute_floatingip_list_view(floating_ips):
    floating_ips = map(compute_ip_to_dict, floating_ips)
    return json.dumps({'floating_ips': floating_ips})


def _compute_floatingip_details_view(floating_ip):
    return json.dumps({'floating_ip': compute_ip_to_dict(floating_ip)})

urlpatterns = patterns(
    'synnefo.api.floating_ips',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_floating_ips', {'detail': True}),
    (r'^/(\w+)(?:/|.json|.xml)?$', 'floating_ip_demux'),
    (r'^/(\w+)/action(?:.json|.xml)?$', 'floating_ip_action_demux'),
)

compute_urlpatterns = patterns(
    'synnefo.api.floating_ips',
    (r'^(?:/|.json|.xml)?$', 'compute_demux'),
    (r'^/(\w+)(?:/|.json|.xml)?$', 'compute_floating_ip_demux'),
)


def demux(request):
    if request.method == 'GET':
        return list_floating_ips(request)
    elif request.method == 'POST':
        return allocate_floating_ip(request)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def floating_ip_demux(request, floating_ip_id):
    if request.method == 'GET':
        return get_floating_ip(request, floating_ip_id)
    elif request.method == 'DELETE':
        return release_floating_ip(request, floating_ip_id)
    elif request.method == 'PUT':
        return update_floating_ip(request, floating_ip_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'DELETE'])


def compute_demux(request):
    if request.method == 'GET':
        return list_floating_ips(request, _compute_floatingip_list_view)
    elif request.method == 'POST':
        return allocate_floating_ip(request, _compute_floatingip_details_view)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'POST'])


def compute_floating_ip_demux(request, floating_ip_id):
    if request.method == 'GET':
        return get_floating_ip(request, floating_ip_id,
                               _compute_floatingip_details_view)
    elif request.method == 'DELETE':
        return release_floating_ip(request, floating_ip_id)
    else:
        return api.api_method_not_allowed(request,
                                          allowed_methods=['GET', 'DELETE'])


@api.api_method(http_method='POST', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def floating_ip_action_demux(request, floating_ip_id):
    userid = request.user_uniq
    req = utils.get_json_body(request)

    log.debug("User %s, Floating IP %s, Request: %s",
              userid, floating_ip_id, req)

    if len(req) != 1:
        raise faults.BadRequest('Malformed request.')

    floating_ip = util.get_floating_ip_by_id(userid,
                                             request.user_projects,
                                             floating_ip_id,
                                             for_update=True)
    action = req.keys()[0]
    try:
        f = FLOATING_IP_ACTIONS[action]
    except KeyError:
        raise faults.BadRequest("Action %s not supported." % action)
    action_args = req[action]
    if not isinstance(action_args, dict):
        raise faults.BadRequest("Invalid argument.")

    return f(request, floating_ip, action_args)


@api.api_method(http_method="GET", user_required=True, logger=log,
                serializations=["json"])
def list_floating_ips(request, view=_floatingip_list_view):
    """Return user reserved floating IPs"""
    floating_ips = IPAddress.objects.for_user(userid=request.user_uniq,
                                              projects=request.user_projects)\
                                    .filter(floating_ip=True)\
                                    .order_by("id")\
                                    .select_related("nic")

    floating_ips = utils.filter_modified_since(request, objects=floating_ips)

    return HttpResponse(view(floating_ips), status=200)


@api.api_method(http_method="GET", user_required=True, logger=log,
                serializations=["json"])
def get_floating_ip(request, floating_ip_id, view=_floatingip_details_view):
    """Return information for a floating IP."""
    floating_ip = util.get_floating_ip_by_id(request.user_uniq,
                                             request.user_projects,
                                             floating_ip_id)
    return HttpResponse(view(floating_ip), status=200)


@api.api_method(http_method='POST', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def allocate_floating_ip(request, view=_floatingip_details_view):
    """Allocate a floating IP."""
    req = utils.get_json_body(request)

    log.debug("User: %s, Action: create_floating_ip, Request: %s",
              request.user_uniq, req)

    floating_ip_dict = api.utils.get_attribute(req, "floatingip",
                                               required=True, attr_type=dict)
    userid = request.user_uniq
    project = floating_ip_dict.get("project", None)
    shared_to_project = floating_ip_dict.get("shared_to_project", False)

    # the network_pool is a mandatory field
    network_id = api.utils.get_attribute(floating_ip_dict,
                                         "floating_network_id",
                                         required=False,
                                         attr_type=(basestring, int))

    if network_id is None:
        floating_ip = \
            ips.create_floating_ip(userid, project=project,
                                   shared_to_project=shared_to_project)
    else:
        try:
            network_id = int(network_id)
        except ValueError:
            raise faults.BadRequest("Invalid networkd ID.")

        network = util.get_network(network_id, userid, request.user_projects,
                                   for_update=True, non_deleted=True)
        address = api.utils.get_attribute(floating_ip_dict,
                                          "floating_ip_address",
                                          required=False,
                                          attr_type=basestring)
        floating_ip = \
            ips.create_floating_ip(userid, network, address,
                                   project=project,
                                   shared_to_project=shared_to_project)

    log.info("User %s created floating IP %s, network %s, address %s",
             userid, floating_ip.id, floating_ip.network_id,
             floating_ip.address)

    return HttpResponse(view(floating_ip), status=200)


@api.api_method(http_method='DELETE', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def release_floating_ip(request, floating_ip_id):
    """Release a floating IP."""
    userid = request.user_uniq

    log.debug("User: %s, Floating IP: %s, Action: delete",
              request.user_uniq, floating_ip_id)

    floating_ip = util.get_floating_ip_by_id(userid, request.user_projects,
                                             floating_ip_id, for_update=True)

    ips.delete_floating_ip(floating_ip)

    log.info("User %s deleted floating IP %s", request.user_uniq,
             floating_ip.id)

    return HttpResponse(status=204)


@api.api_method(http_method='PUT', user_required=True, logger=log,
                serializations=["json"])
@transaction.commit_on_success
def update_floating_ip(request, floating_ip_id, view=_floatingip_details_view):
    """Update a floating IP."""
    raise faults.NotImplemented("Updating a floating IP is not supported.")
    #userid = request.user_uniq
    #log.info("update_floating_ip '%s'. User '%s'.", floating_ip_id, userid)

    #req = utils.get_json_body(request)
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


def reassign(request, floating_ip, args):
    if request.user_uniq != floating_ip.userid:
        raise faults.Forbidden("Action 'reassign' is allowed only to the owner"
                               " of the floating IP.")

    shared_to_project = args.get("shared_to_project", False)
    if shared_to_project and not settings.CYCLADES_SHARED_RESOURCES_ENABLED:
        raise faults.Forbidden("Sharing resource to the members of the project"
                                " is not permitted")

    project = args.get("project")
    if project is None:
        raise faults.BadRequest("Missing 'project' attribute.")

    ips.reassign_floating_ip(floating_ip, project, shared_to_project)

    log.info("User %s reaasigned floating IP %s to project %s, shared: %s",
             request.user_uniq, floating_ip.id, project, shared_to_project)

    return HttpResponse(status=200)


FLOATING_IP_ACTIONS = {
    "reassign": reassign,
}


def network_to_floating_ip_pool(network):
    """Convert a 'Network' object to a floating IP pool dict."""
    total, free = network.ip_count()
    return {"name": str(network.id),
            "size": total,
            "free": free,
            "deleted": network.deleted}

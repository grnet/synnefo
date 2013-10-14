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
from synnefo.db.models import NetworkInterface, SecurityGroup, IPAddress
from synnefo.logic import ports

from logging import getLogger

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.ports',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/([-\w]+)(?:/|.json|.xml)?$', 'port_demux'))


def demux(request):
    if request.method == 'GET':
        return list_ports(request)
    elif request.method == 'POST':
        return create_port(request)
    else:
        return api.api_method_not_allowed(request)


def port_demux(request, port_id):

    if request.method == 'GET':
        return get_port_details(request, port_id)
    elif request.method == 'DELETE':
        return delete_port(request, port_id)
    elif request.method == 'PUT':
        return update_port(request, port_id)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_ports(request, detail=False):

    log.debug('list_ports detail=%s', detail)

    user_ports = NetworkInterface.objects.filter(
        network__userid=request.user_uniq)

    port_dicts = [port_to_dict(port, detail)
             for port in user_ports.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_ports.xml', {
            "ports": port_dicts})
    else:
        data = json.dumps({'ports': port_dicts})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
def create_port(request):
    '''
    '''
    user_id = request.user_uniq
    req = api.utils.get_request_dict(request)
    log.info('create_port %s', req)

    port_dict = api.utils.get_attribute(req, "port")
    net_id = api.utils.get_attribute(port_dict, "network_id")
    dev_id = api.utils.get_attribute(port_dict, "device_id")

    network = util.get_network(net_id, request.user_uniq, non_deleted=True)

    if network.public:
        raise api.faults.Forbidden('forbidden')


    vm = util.get_vm(dev_id, request.user_uniq)

    name = api.utils.get_attribute(port_dict, "name", required=False)

    if name is None:
        name = ""

    sg_list = []
    security_groups = api.utils.get_attribute(port_dict,
                                              "security_groups",
                                              required=False)
    #validate security groups
    # like get security group from db
    if security_groups:
        for gid in security_groups:
            try:
                sg = SecurityGroup.objects.get(id=int(gid))
                sg_list.append(sg)
            except (ValueError, SecurityGroup.DoesNotExist):
                raise api.faults.ItemNotFound("Not valid security group")

    new_port = ports.create(user_id, network, vm, security_groups=sg_list)

    response = render_port(request, port_to_dict(new_port), status=201)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_port_details(request, port_id):
    log.debug('get_port_details %s', port_id)
    port = util.get_port(port_id, request.user_uniq)
    return render_port(request, port_to_dict(port))


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_port(request, port_id):
    '''
    You can update only name, security_groups
    '''
    port = util.get_port(port_id, request.user_uniq, for_update=True)
    req = api.utils.get_request_dict(request)

    port_info = api.utils.get_attribute(req, "port", required=True)
    name = api.utils.get_attribute(port_info, "name", required=False)

    if name:
        port.name = name

    security_groups = api.utils.get_attribute(port_info, "security_groups",
                                              required=False)
    if security_groups:
        sg_list = []
        #validate security groups
        # like get security group from db
        for gid in security_groups:
            try:
                sg = SecurityGroup.objects.get(id=int(gid))
                sg_list.append(sg)
            except (ValueError, SecurityGroup.DoesNotExist):
                raise api.faults.ItemNotFound("Not valid security group")

        #clear the old security groups
        port.security_groups.clear()

        #add the new groups
        port.security_groups.add(*sg_list)

    port.save()
    return render_port(request, port_to_dict(port), 200)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_port(request, port_id):
    log.info('delete_port %s', port_id)
    port = util.get_port(port_id, request.user_uniq, for_update=True)
    '''
    FIXME delete the port
    skip the backend part...
    release the ips associated with the port
    '''
    return HttpResponse(status=204)

#util functions


def port_to_dict(port, detail=True):
    d = {'id': str(port.id), 'name': port.name}
    if detail:
        d['user_id'] = port.network.userid
        d['tenant_id'] = port.network.userid
        d['device_id'] = str(port.machine.id)
        d['admin_state_up'] = True
        d['mac_address'] = port.mac
        d['status'] = port.state
        d['device_owner'] = port.device_owner
        d['network_id'] = str(port.network.id)
        d['updated'] = api.utils.isoformat(port.updated)
        d['created'] = api.utils.isoformat(port.created)
        d['fixed_ips'] = []
        for ip in port.ips.all():
            d['fixed_ips'].append({"ip_address": ip.address,
                                      "subnet": str(ip.subnet.id)})
        sg_list = list(port.security_groups.values_list('id', flat=True))
        d['security_groups'] = map(str, sg_list)

    return d


def render_port(request, portdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('port.xml', {'port': portdict})
    else:
        data = json.dumps({'port': portdict})
    return HttpResponse(data, status=status)

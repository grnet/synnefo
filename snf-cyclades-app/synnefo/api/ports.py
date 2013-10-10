from django.conf import settings
from django.conf.urls import patterns

from django.http import HttpResponse
from django.utils import simplejson as json
from django.db import transaction
from django.db.models import Q
from synnefo.db.pools import EmptyPool
from synnefo.db.utils import validate_mac
from django.conf import settings
from snf_django.lib import api
from snf_django.lib.api import utils
from synnefo.logic import backend
from django.template.loader import render_to_string
from synnefo.api import util
from synnefo.db.models import NetworkInterface, SecurityGroup, IPAddress

from logging import getLogger

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.ports',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/([-\w]+)(?:/|.json|.xml)?$', 'port_demux'))

def demux(request):
    if request.method == 'GET':
        #return HttpResponse("list ports")
        return list_ports(request)
    elif request.method == 'POST':
        return create_port(request)
        #return HttpResponse("create port")
    else:
        return api.api_method_not_allowed(request)


def port_demux(request, offset):

    if request.method == 'GET':
        #return HttpResponse("get single port")
        return get_port(request, offset)
    elif request.method == 'DELETE':
        #return HttpResponse("delete port")
        return delete_port(request, offset)
    elif request.method == 'PUT':
        #return HttpResponse("put port")
        return update_port(request, offset)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_ports(request, detail=False):

    log.debug('list_ports detail=%s', detail)

    user_ports = NetworkInterface.objects.filter(
        network__userid=request.user_uniq)

    ports = [port_to_dict(port, detail)
             for port in user_ports.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {
            "ports": ports})
    else:
        data = json.dumps({'ports': ports})

    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_port(request, port_id):
    log.debug('get_port_details %s', port_id)
    port = util.get_port(port_id, request.user_uniq)

    portdict = port_to_dict(port)
    return render_port(request, portdict)


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


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_port(request, port_id):
    '''
    You can update only name, security_groups
    '''
    port = util.get_port(port_id, request.user_uniq, for_update=True)
    info = utils.get_request_dict(request)
    try:
        info = info["port"]
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    try:
        name = info['name']
        port.name = name
    except KeyError:
        pass
    sg_list = []
    try:
        s_groups = info['security_groups']
        #validate security groups
        # like get security group from db
        for gid in s_groups:
            try:
                sg = SecurityGroup.objects.get(id=int(gid))
                sg_list.append(sg)
            except (ValueError, SecurityGroup.DoesNotExist):
                raise api.faults.ItemNotFound("Not valid security group")

        #clear the old security groups
        port.security_groups.clear()

        #add the new groups
        for group in sg_list:
            port.security_groups.add(group)
    except KeyError:
        pass

    port.save()
    portdict = port_to_dict(port)
    return render_port(request, portdict, 200)


@api.api_method(http_method='POST', user_required=True, logger=log)
@transaction.commit_manually
def create_port(request):
    '''
    '''
    user_id = request.user_uniq
    req = utils.get_request_dict(request)
    log.info('create_port %s', req)
    try:
        try:
            info = req['port']
            net_id = info['network_id']
            dev_id = info['device_id']
        except KeyError:
            raise api.faults.BadRequest("Malformed request")

        net = util.get_network(net_id, request.user_uniq)

        vm = util.get_vm(dev_id, request.user_uniq)

        try:
            name = info['name']
        except KeyError:
            name = "random_name"

        sg_list = []
        try:
            s_groups = info['security_groups']
            #validate security groups
            # like get security group from db
            for gid in s_groups:
                try:
                    sg = SecurityGroup.objects.get(id=int(gid))
                    sg_list.append(sg)
                except (ValueError, SecurityGroup.DoesNotExist):
                    raise api.faults.ItemNotFound("Not valid security group")
        except KeyError:
            pass

        #create the port
        new_port = NetworkInterface.objects.create(name=name,
                                                   network=net,
                                                   machine=vm,
                                                   device_owner="vm",
                                                   state="BUILDING")
        #add the security groups
        new_port.security_groups.add(*sg_list)

        #add every to every subnet of the network
        for subn in net.subnets.all():
            IPAddress.objects.create(subnet=subn,
                                     network=net,
                                     nic=new_port,
                                     userid=user_id,
                                     address="192.168.0."+str(subn.id)  # FIXME
                                     )


    except:
        transaction.rollback()
        log.info("roll")
        raise

    else:
        transaction.commit()
        log.info("commit")

    portdict = port_to_dict(new_port)
    response = render_port(request, portdict, status=201)

    return response


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
        d['fixed_ips'] = []
        for ip in port.ips.all():
            d['fixed_ips'].append({"ip_address": ip.address,
                                      "subnet": ip.subnet.id})
        d['security_groups'] = [str(sg.id)
                                for sg in port.security_groups.all()]
    return d


def render_port(request, portdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'port': portdict})
    else:
        data = json.dumps({'port': portdict})
    return HttpResponse(data, status=status)

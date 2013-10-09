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
from synnefo.db.models import Network

from logging import getLogger

from synnefo import quotas

log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.networks',
     (r'^(?:/|.json|.xml)?$', 'demux'),
     (r'^/(\w+)(?:/|.json|.xml)?$', 'network_demux'))

def demux(request):
    if request.method == 'GET':
        #return HttpResponse("in network get")
        return list_networks(request)
    elif request.method == 'POST':
        return create_network(request)
        #return HttpResponse("in network post")
    else:
        return api.api_method_not_allowed(request)


def network_demux(request, offset):

    if request.method == 'GET':
        return get_network(request, offset)
        #return HttpResponse("in network det get")
    elif request.method == 'DELETE':
        return delete_network(request, offset)
        #return HttpResponse("in network det delete")
    elif request.method == 'PUT':
        return update_network(request, offset)
        #return HttpResponse("in network det put")
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_networks(request, detail=False):
    log.debug('list_networks detail=%s', detail)

    user_networks = Network.objects.filter(
        Q(userid=request.user_uniq) | Q(public=True))

    user_networks = utils.filter_modified_since(request, objects=user_networks)

    networks = [network_to_dict(network, detail)
                for network in user_networks.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {
            "networks": networks})
    else:
        data = json.dumps({'networks': networks})

    return HttpResponse(data, status=200)


@api.api_method(http_method='POST', user_required=True, logger=log)
@transaction.commit_manually
def create_network(request):
    try:
        user_id = request.user_uniq
        req = utils.get_request_dict(request)
        log.info('create_network %s', req)
        try:
            d = req['network']
        except KeyError:
            raise api.faults.BadRequest("Malformed request")

        try:
            flavor = d['type']
        except KeyError:
            raise faults.BadRequest("Missing request parameter 'type'")

        if flavor not in Network.FLAVORS.keys():
            raise api.faults.BadRequest("Invalid network type '%s'"
                                        % flavor)
        if flavor not in settings.API_ENABLED_NETWORK_FLAVORS:
            msg = "Can not create network of type '%s'"
            raise api.faults.Forbidden(msg % flavor)

        try:
            name = d['name']
        except KeyError:
            name = ""

        try:
            #mode, link, mac_prefix, tags = util.values_from_flavor(flavor)

            #validate_mac(mac_prefix + "0:00:00:00")
            network = Network.objects.create(
                name=name,
                userid=user_id,
                flavor=flavor,
                #mode=mode,
                #link=link,
                #mac_prefix=mac_prefix,
                #tags=tags,
                action='CREATE',
                state='ACTIVE')
        except EmptyPool:
            msg = "Failed to allocate resources for network of type: %s"
            log.error(msg, flavor)
            raise api.faults.ServiceUnavailable("Failed to allocate network\
                  resources")

        # Issue commission to Quotaholder and accept it since at the end of
        # this transaction the Network object will be created in the DB.
        # Note: the following call does a commit!
        #quotas.issue_and_accept_commission(network)
        # COME BACK....

    except:
        transaction.rollback()
        log.info("roll")
        raise
    else:
        transaction.commit()
        log.info("commit")
    networkdict = network_to_dict(network)
    response = render_network(request, networkdict, status=201)

    return response


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_network(request, network_id):
    log.debug('get_network_details %s', network_id)
    net = util.get_network(network_id, request.user_uniq)

    #needs discussion
    if net.deleted:
        raise api.faults.BadRequest("Network has been deleted.")
    else:
        netdict = network_to_dict(net)
        return render_network(request, netdict)


@api.api_method(http_method='DELETE', user_required=True, logger=log)
@transaction.commit_on_success
def delete_network(request, network_id):
    log.info('delete_network %s', network_id)
    net = util.get_network(network_id, request.user_uniq, for_update=True)

    log.info(net.name)
    if net.public:
        raise api.faults.Forbidden('Can not delete the public network.')

    if net.deleted:
        raise api.faults.BadRequest("Network has been deleted.")

    if net.machines.all():  # Nics attached on network
        #raise api.faults.NetworkInUse('Machines are connected to network.')
        #edit to return with 409
        return HttpResponse("Network in use", status=409)

    #check if there are any floating ips reserved
    #if net.floating_ips.all():
    #    #raise api.faults.NetworkInUse('Machines are connected to network.')
    #    #edit to return with 409
    #    return HttpResponse("Network in use", status=409)

    net.action = 'DESTROY'
    '''
    skip the backend part...
    backend_networks = net.backend_networks.exclude(operstate="DELETED")
    for bnet in backend_networks:
        backend.delete_network(net, bnet.backend)
    if not backend_networks:
        backend.update_network_state(net)
    '''

    #delete all the subnets

    for s in net.subnets.all():
        s.deleted = True

    #the following has to leave when fix the backend thing
    net.deleted = True
    net.save()

    return HttpResponse(status=204)


@api.api_method(http_method='PUT', user_required=True, logger=log)
def update_network(request, network_id):
    '''
    You can update only name
    '''
    net = util.get_network(network_id, request.user_uniq, for_update=True)
    info = utils.get_request_dict(request)

    updatable = set(["name"])
    try:
        new_vals = info["network"]
    except KeyError:
        raise api.faults.BadRequest("Malformed request")

    for key, val in new_vals.iteritems():
        if key in updatable:
            setattr(net, key, val)
        else:
            raise api.faults.BadRequest("Wrong field update")
    net.save()
    netdict = network_to_dict(net)
    return render_network(request, netdict, 200)


def network_to_dict(network, detail=True):
    d = {'id': str(network.id), 'name': network.name}
    d['links'] = util.network_to_links(network.id)
    if detail:
        d['user_id'] = network.userid
        d['tenant_id'] = network.userid
        d['type'] = network.flavor
        d['updated'] = utils.isoformat(network.updated)
        d['created'] = utils.isoformat(network.created)
        d['status'] = network.state
        d['public'] = network.public
        d['external_router'] = network.external_router
        d['external_router'] = network.external_router
        d['admin_state_up'] = True
        subnet_cidr = [s.id for s in network.subnets.all()]
        d['subnets'] = subnet_cidr
    return d


def render_network(request, networkdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'network': networkdict})
    else:
        data = json.dumps({'network': networkdict})
    return HttpResponse(data, status=status)

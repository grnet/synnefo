from synnefo.api.actions import network_actions
from synnefo.api.common import method_not_allowed
from synnefo.api.faults import BadRequest, Unauthorized
from synnefo.api.util import (isoformat, isoparse, get_network,
                                get_request_dict, api_method)
from synnefo.db.models import Network

from django.conf.urls.defaults import patterns
from django.http import HttpResponse
from django.utils import simplejson as json


urlpatterns = patterns('synnefo.api.networks',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_networks', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'network_demux'),
    (r'^/(\d+)/action(?:.json|.xml)?$', 'network_action'),
)


def demux(request):
    if request.method == 'GET':
        return list_networks(request)
    elif request.method == 'POST':
        return create_network(request)
    else:
        return method_not_allowed(request)

def network_demux(request, network_id):
    if request.method == 'GET':
        return get_network_details(request, network_id)
    elif request.method == 'PUT':
        return update_network_name(request, network_id)
    elif request.method == 'DELETE':
        return delete_network(request, network_id)
    else:
        return method_not_allowed(request)


def network_to_dict(network, detail=True):
    d = {'id': network.id, 'name': network.name}
    if detail:
        d['servers'] = {'values': [vm.id for vm in network.machines.all()]}
    return d

def render_network(request, networkdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'network': networkdict})
    else:
        data = json.dumps({'network': networkdict})
    return HttpResponse(data, status=status)


@api_method('GET')
def list_networks(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    since = isoparse(request.GET.get('changes-since'))

    if since:
        user_networks = Network.objects.filter(owner=request.user, updated__gte=since)
        if not user_networks:
            return HttpResponse(status=304)
    else:
        user_networks = Network.objects.filter(owner=request.user)

    networks = [network_to_dict(network, detail) for network in user_networks]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {'networks': networks, 'detail': detail})
    else:
        data = json.dumps({'networks': {'values': networks}})

    return HttpResponse(data, status=200)

@api_method('POST')
def create_network(request):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badMediaType(415),
    #                       badRequest (400),
    #                       overLimit (413)

    req = get_request_dict(request)

    try:
        d = req['network']
        name = d['name']
    except (KeyError, ValueError):
        raise BadRequest('Malformed request.')

    network = Network.objects.create(name=name, owner=request.user)
    networkdict = network_to_dict(network)
    return render_network(request, networkdict, status=202)

@api_method('GET')
def get_network_details(request, network_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    net = get_network(network_id, request.user)
    netdict = network_to_dict(net)
    return render_network(request, netdict)

@api_method('PUT')
def update_network_name(request, network_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    req = get_request_dict(request)

    try:
        name = req['network']['name']
    except (TypeError, KeyError):
        raise BadRequest('Malformed request.')

    net = get_network(network_id, request.user)
    net.name = name
    net.save()
    return HttpResponse(status=204)

@api_method('DELETE')
def delete_network(request, network_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       overLimit (413)

    net = get_network(network_id, request.user)
    net.delete()
    return HttpResponse(status=204)

@api_method('POST')
def network_action(request, network_id):
    net = get_network(network_id, request.user)
    req = get_request_dict(request)
    if len(req) != 1:
        raise BadRequest('Malformed request.')

    key = req.keys()[0]
    val = req[key]

    try:
        assert isinstance(val, dict)
        return network_actions[key](request, net, req[key])
    except KeyError:
        raise BadRequest('Unknown action.')
    except AssertionError:
        raise BadRequest('Invalid argument.')

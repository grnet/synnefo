from django.conf.urls.defaults import patterns
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from synnefo.api import util
from synnefo.api.actions import network_actions
from synnefo.api.common import method_not_allowed
from synnefo.api.faults import BadRequest, OverLimit, Unauthorized
from synnefo.db.models import Network
from synnefo.logic import backend


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
    network_id = str(network.id) if not network.public else 'public'
    d = {'id': network_id, 'name': network.name}
    if detail:
        d['updated'] = util.isoformat(network.updated)
        d['created'] = util.isoformat(network.created)
        d['servers'] = {'values': [vm.id for vm in network.machines.all()]}
        d['status'] = network.state
    return d

def render_network(request, networkdict, status=200):
    if request.serialization == 'xml':
        data = render_to_string('network.xml', {'network': networkdict})
    else:
        data = json.dumps({'network': networkdict})
    return HttpResponse(data, status=status)


@util.api_method('GET')
def list_networks(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    owner = request.user
    since = util.isoparse(request.GET.get('changes-since'))
    user_networks = Network.objects.filter(Q(owner=owner) | Q(public=True))
    
    if since:
        user_networks = user_networks.filter(updated__gte=since)
        if not user_networks:
            return HttpResponse(status=304)
    else:
        user_networks = user_networks.filter(state='ACTIVE')
    
    networks = [network_to_dict(network, detail) for network in user_networks]

    if request.serialization == 'xml':
        data = render_to_string('list_networks.xml', {
            'networks': networks,
            'detail': detail})
    else:
        data = json.dumps({'networks': {'values': networks}})

    return HttpResponse(data, status=200)

@util.api_method('POST')
def create_network(request):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badMediaType(415),
    #                       badRequest (400),
    #                       overLimit (413)

    req = util.get_request_dict(request)

    try:
        d = req['network']
        name = d['name']
    except (KeyError, ValueError):
        raise BadRequest('Malformed request.')
    
    network = Network.objects.create(
        name=name,
        owner=request.user,
        state='ACTIVE')
    
    if not backend.create_network(network):
        network.delete()
        raise OverLimit('Maximum number of networks reached.')
    
    networkdict = network_to_dict(network)
    return render_network(request, networkdict, status=202)

@util.api_method('GET')
def get_network_details(request, network_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    net = util.get_network(network_id, request.user)
    netdict = network_to_dict(net)
    return render_network(request, netdict)

@util.api_method('PUT')
def update_network_name(request, network_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       overLimit (413)

    req = util.get_request_dict(request)

    try:
        name = req['network']['name']
    except (TypeError, KeyError):
        raise BadRequest('Malformed request.')

    net = util.get_network(network_id, request.user)
    if net.public:
        raise Unauthorized('Can not rename the public network.')
    net.name = name
    net.save()
    return HttpResponse(status=204)

@util.api_method('DELETE')
def delete_network(request, network_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       unauthorized (401),
    #                       overLimit (413)
    
    net = util.get_network(network_id, request.user)
    if net.public:
        raise Unauthorized('Can not delete the public network.')
    backend.delete_network(net)
    return HttpResponse(status=204)

@util.api_method('POST')
def network_action(request, network_id):
    net = util.get_network(network_id, request.user)
    if net.public:
        raise Unauthorized('Can not modify the public network.')
    
    req = util.get_request_dict(request)
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

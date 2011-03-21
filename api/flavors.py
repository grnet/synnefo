#
# Copyright (c) 2010 Greek Research and Technology Network
#

from synnefo.api.util import *
from synnefo.db.models import Flavor

from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.template.loader import render_to_string


urlpatterns = patterns('synnefo.api.flavors',
    (r'^(?:/|.json|.xml)?$', 'list_flavors'),
    (r'^/detail(?:.json|.xml)?$', 'list_flavors', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'get_flavor_details'),
)


def flavor_to_dict(flavor, detail=True):
    d = {'id': flavor.id, 'name': flavor.name}
    if detail:
        d['ram'] = flavor.ram
        d['disk'] = flavor.disk
    return d


@api_method('GET')
def list_flavors(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    all_flavors = Flavor.objects.all()
    flavors = [flavor_to_dict(flavor, detail) for flavor in all_flavors]
    
    if request.type == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('list_flavors.xml', {'flavors': flavors, 'detail': detail})
    else:
        mimetype = 'application/json'
        data = json.dumps({'flavors': {'values': flavors}})
    
    return HttpResponse(data, mimetype=mimetype, status=200)

@api_method('GET')
def get_flavor_details(request, flavor_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    try:
        falvor_id = int(flavor_id)
        flavor = flavor_to_dict(Flavor.objects.get(id=flavor_id))
    except Flavor.DoesNotExist:
        raise ItemNotFound
    
    if request.type == 'xml':
        data = render_to_string('flavor.xml', {'flavor': flavor})
    else:
        data = json.dumps({'flavor': flavor})
    
    return HttpResponse(data, status=200)

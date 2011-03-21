#
# Copyright (c) 2010 Greek Research and Technology Network
#

from synnefo.api.util import *
from synnefo.db.models import Image

from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.template.loader import render_to_string


urlpatterns = patterns('synnefo.api.images',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/detail(?:.json|.xml)?$', 'list_images', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'image_demux'),
)

def demux(request):
    if request.method == 'GET':
        return list_images(request)
    elif request.method == 'POST':
        return create_image(request)
    else:
        fault = BadRequest()
        return render_fault(request, fault)

def image_demux(request, image_id):
    if request.method == 'GET':
        return get_image_details(request, image_id)
    elif request.method == 'DELETE':
        return delete_image(request, image_id)
    else:
        fault = BadRequest()
        return render_fault(request, fault)


def image_to_dict(image, detail=True):
    d = {'id': image.id, 'name': image.name}
    if detail:
        d['updated'] = image.updated.isoformat()
        d['created'] = image.created.isoformat()
        d['status'] = image.state
        d['progress'] = 100 if image.state == 'ACTIVE' else 0
        d['description'] = image.description
        if image.sourcevm:
            d['serverRef'] = image.sourcevm.id
    return d


@api_method('GET')
def list_images(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)
    
    all_images = Image.objects.all()
    images = [image_to_dict(image, detail) for image in all_images]
    
    if request.type == 'xml':
        mimetype = 'application/xml'
        data = render_to_string('list_images.xml', {'images': images, 'detail': detail})
    else:
        mimetype = 'application/json'
        data = json.dumps({'images': {'values': images}})
    
    return HttpResponse(data, mimetype=mimetype, status=200)

@api_method('POST')
def create_image(request):
    # Normal Response Code: 202
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badMediaType(415),
    #                       itemNotFound (404),
    #                       badRequest (400),
    #                       serverCapacityUnavailable (503),
    #                       buildInProgress (409),
    #                       resizeNotAllowed (403),
    #                       backupOrResizeInProgress (409),
    #                       overLimit (413)
    
    req = get_request_dict(request)
    owner = get_user()
    
    try:
        d = req['image']
        server_id = int(d['serverRef'])
        vm = VirtualMachine.objects.get(id=server_id)
        image = Image.objects.create(name=d['name'], size=0, owner=owner, sourcevm=vm)
        image.save()
    except KeyError:
        raise BadRequest
    except ValueError:
        raise BadRequest
    except VirtualMachine.DoesNotExist:
        raise ItemNotFound
    
    imagedict = image_to_dict(image)
    if request.type == 'xml':
        data = render_to_string('image.xml', {'image': imagedict})
    else:
        data = json.dumps({'image': imagedict})
    
    return HttpResponse(data, status=202)

@api_method('GET')
def get_image_details(request, image_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    try:
        image_id = int(image_id)
        imagedict = image_to_dict(Image.objects.get(id=image_id))
    except Image.DoesNotExist:
        raise ItemNotFound
    
    if request.type == 'xml':
        data = render_to_string('image.xml', {'image': imagedict})
    else:
        data = json.dumps({'image': imagedict})
    
    return HttpResponse(data, status=200)

@api_method('DELETE')
def delete_image(request, image_id):
    # Normal Response Code: 204
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       itemNotFound (404),
    #                       overLimit (413)
    
    try:
        image_id = int(image_id)
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        raise ItemNotFound
    
    if image.owner != get_user():
        raise Unauthorized()
    image.delete()
    return HttpResponse(status=204)

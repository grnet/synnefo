# Copyright (C) 2010-2014 GRNET S.A.
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

from logging import getLogger
from django.conf.urls import patterns

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import simplejson as json

from snf_django.lib import api
from synnefo.api import util
from synnefo.db.models import Flavor


log = getLogger('synnefo.api')


urlpatterns = patterns(
    'synnefo.api.flavors',
    (r'^(?:/|.json|.xml)?$', 'list_flavors'),
    (r'^/detail(?:.json|.xml)?$', 'list_flavors', {'detail': True}),
    (r'^/(\d+)(?:.json|.xml)?$', 'get_flavor_details'),
)


def flavor_to_dict(flavor, detail=True):
    d = {'id': flavor.id, 'name': flavor.name}
    d['links'] = util.flavor_to_links(flavor.id)
    if detail:
        d['ram'] = flavor.ram
        d['disk'] = flavor.disk
        d['vcpus'] = flavor.cpu
        d['SNF:disk_template'] = flavor.volume_type.disk_template
        d['SNF:volume_type'] = flavor.volume_type_id
        d['SNF:allow_create'] = flavor.allow_create
    return d


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_flavors(request, detail=False):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       overLimit (413)

    log.debug('list_flavors detail=%s', detail)
    active_flavors = Flavor.objects.select_related("volume_type")\
                                   .exclude(deleted=True)
    flavors = [flavor_to_dict(flavor, detail)
               for flavor in active_flavors.order_by('id')]

    if request.serialization == 'xml':
        data = render_to_string('list_flavors.xml', {
            'flavors': flavors,
            'detail': detail})
    else:
        data = json.dumps({'flavors': flavors})

    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_flavor_details(request, flavor_id):
    # Normal Response Codes: 200, 203
    # Error Response Codes: computeFault (400, 500),
    #                       serviceUnavailable (503),
    #                       unauthorized (401),
    #                       badRequest (400),
    #                       itemNotFound (404),
    #                       overLimit (413)

    log.debug('get_flavor_details %s', flavor_id)
    flavor = util.get_flavor(flavor_id, include_deleted=True)
    flavordict = flavor_to_dict(flavor, detail=True)

    if request.serialization == 'xml':
        data = render_to_string('flavor.xml', {'flavor': flavordict})
    else:
        data = json.dumps({'flavor': flavordict})

    return HttpResponse(data, status=200)

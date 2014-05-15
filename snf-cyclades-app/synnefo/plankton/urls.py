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

from django.conf.urls import patterns, include

from django.http import HttpResponseNotAllowed
from snf_django.lib.api import api_endpoint_not_found

from synnefo.plankton import views


def demux(request):
    if request.method == 'GET':
        return views.list_images(request)
    elif request.method == 'POST':
        return views.add_image(request)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])


def demux_image(request, image_id):
    if request.method == "GET":
        return views.get_image(request, image_id)
    elif request.method == "HEAD":
        return views.get_image_meta(request, image_id)
    elif request.method == "PUT":
        return views.update_image(request, image_id)
    elif request.method == "DELETE":
        return views.delete_image(request, image_id)
    else:
        return HttpResponseNotAllowed(["GET", "HEAD", "PUT", "DELETE"])


def demux_image_members(request, image_id):
    if request.method == 'GET':
        return views.list_image_members(request, image_id)
    elif request.method == 'PUT':
        return views.update_image_members(request, image_id)
    else:
        return HttpResponseNotAllowed(['GET', 'PUT'])


def demux_members(request, image_id, member):
    if request.method == 'DELETE':
        return views.remove_image_member(request, image_id, member)
    elif request.method == 'PUT':
        return views.add_image_member(request, image_id, member)
    else:
        return HttpResponseNotAllowed(['DELETE', 'PUT'])


image_v1_patterns = patterns(
    '',
    (r'^images/$', demux),
    (r'^images/detail$', views.list_images, {'detail': True}),
    (r'^images/([\w-]+)$', demux_image),
    (r'^images/([\w-]+)/members$', demux_image_members),
    (r'^images/([\w-]+)/members/([\w@._-]+)$', demux_members),
    (r'^shared-images/([\w@._-]+)$', views.list_shared_images),
)

urlpatterns = patterns(
    '',
    (r'^v1.0/', include(image_v1_patterns)),
    (r'^.*', api_endpoint_not_found),
)

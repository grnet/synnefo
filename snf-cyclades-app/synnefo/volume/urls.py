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

from django.conf.urls.defaults import patterns, include
from django.http import HttpResponseNotAllowed
from snf_django.lib import api
from synnefo.volume import views


def volume_demux(request):
    if request.method == 'GET':
        return views.list_volumes(request)
    elif request.method == 'POST':
        return views.create_volume(request)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])


def volume_item_demux(request, volume_id):
    if request.method == "GET":
        return views.get_volume(request, volume_id)
    elif request.method == "PUT":
        return views.update_volume(request, volume_id)
    elif request.method == "DELETE":
        return views.delete_volume(request, volume_id)
    else:
        return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


def snapshot_demux(request):
    if request.method == 'GET':
        return views.list_snapshots(request)
    elif request.method == 'POST':
        return views.create_snapshot(request)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])


def snapshot_item_demux(request, snapshot_id):
    if request.method == "GET":
        return views.get_snapshot(request, snapshot_id)
    elif request.method == "PUT":
        return views.update_snapshot(request, snapshot_id)
    elif request.method == "DELETE":
        return views.delete_snapshot(request, snapshot_id)
    else:
        return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])

volume_v2_patterns = patterns(
    '',
    (r'^volumes/$', volume_demux),
    (r'^volumes/detail$', views.list_volumes, {'detail': True}),
    (r'^volumes/(\d+)(?:.json)?$', volume_item_demux),
    (r'^snapshots/$', snapshot_demux),
    (r'^snapshots/detail$', views.list_snapshots, {'detail': True}),
    (r'^snapshots/(\d+)(?:.json)?$', snapshot_item_demux),
    (r'^types/$', views.list_volume_types),
    (r'^types/(\d+)(?:.json)?$', views.get_volume_type),
)

urlpatterns = patterns(
    '',
    (r'^v2.0/', include(volume_v2_patterns)),
    (r'^.*', api.api_endpoint_not_found)
)

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

from django.conf import settings
from django.conf.urls.defaults import patterns, include
from django.http import HttpResponseNotAllowed
from snf_django.lib import api
from synnefo.volume import views
from snf_django.lib.api import faults, utils


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


def volume_metadata_demux(request, volume_id):
    if request.method == 'GET':
        return views.list_volume_metadata(request, volume_id)
    elif request.method == 'POST':
        return views.update_volume_metadata(request, volume_id, reset=False)
    elif request.method == 'PUT':
        return views.update_volume_metadata(request, volume_id, reset=True)
    else:
        return HttpResponseNotAllowed(['GET', 'POST', 'PUT'])


def volume_metadata_item_demux(request, volume_id, key):
    if request.method == 'DELETE':
        return views.delete_volume_metadata_item(request, volume_id, key)
    else:
        return HttpResponseNotAllowed(['DELETE'])


VOLUME_ACTIONS = {
    "reassign": views.reassign_volume,
    }


def volume_action_demux(request, volume_id):
    req = utils.get_json_body(request)

    if not isinstance(req, dict) and len(req) != 1:
        raise faults.BadRequest("Malformed request")

    action = req.keys()[0]
    if not isinstance(action, basestring):
        raise faults.BadRequest("Malformed Request. Invalid action.")

    try:
        action_func = VOLUME_ACTIONS[action]
    except KeyError:
        raise faults.BadRequest("Action %s not supported" % action)
    action_args = utils.get_attribute(req, action, required=True,
                                      attr_type=dict)

    return action_func(request, volume_id, action_args)


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


def snapshot_metadata_demux(request, snapshot_id):
    if request.method == 'GET':
        return views.list_snapshot_metadata(request, snapshot_id)
    elif request.method == 'POST':
        return views.update_snapshot_metadata(request, snapshot_id,
                                              reset=False)
    elif request.method == 'PUT':
        return views.update_snapshot_metadata(request, snapshot_id, reset=True)
    else:
        return HttpResponseNotAllowed(['GET', 'POST', 'PUT'])


def snapshot_metadata_item_demux(request, snapshot_id, key):
    if request.method == 'DELETE':
        return views.delete_snapshot_metadata_item(request, snapshot_id, key)
    else:
        return HttpResponseNotAllowed(['DELETE'])


volume_v2_patterns = patterns(
    '',
    (r'^volumes/?(?:.json)?$', volume_demux),
    (r'^volumes/detail(?:.json)?$', views.list_volumes, {'detail': True}),
    (r'^volumes/(\d+)(?:.json)?$', volume_item_demux),
    (r'^volumes/(\d+)/metadata/?(?:.json)?$', volume_metadata_demux),
    (r'^volumes/(\d+)/metadata/(.+)(?:.json)?$', volume_metadata_item_demux),
    (r'^volumes/(\d+)/action(?:.json|.xml)?$', volume_action_demux),
    (r'^types/?(?:.json)?$', views.list_volume_types),
    (r'^types/(\d+)(?:.json)?$', views.get_volume_type),
)

if settings.CYCLADES_SNAPSHOTS_ENABLED:
    volume_v2_patterns += patterns(
        '',
        (r'^snapshots/?(?:.json)?$', snapshot_demux),
        (r'^snapshots/detail$', views.list_snapshots, {'detail': True}),
        (r'^snapshots/([\w-]+)(?:.json)?$', snapshot_item_demux),
        (r'^snapshots/([\w-]+)/metadata/?(?:.json)?$',
            snapshot_metadata_demux),
        (r'^snapshots/([\w-]+)/metadata/(.+)(?:.json)?$',
            snapshot_metadata_item_demux),
    )

urlpatterns = patterns(
    '',
    (r'^v2.0/', include(volume_v2_patterns)),
    (r'^.*', api.api_endpoint_not_found)
)

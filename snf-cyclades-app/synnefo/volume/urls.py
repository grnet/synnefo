# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

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
)

urlpatterns = patterns(
    '',
    (r'^v2.0/', include(volume_v2_patterns)),
    (r'^.*', api.api_endpoint_not_found)
)

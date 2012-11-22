# Copyright 2011 GRNET S.A. All rights reserved.
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

from django.conf.urls.defaults import patterns
from django.http import HttpResponseNotAllowed

from synnefo.plankton import views


def demux(request):
    if request.method == 'GET':
        return views.list_public_images(request)
    elif request.method == 'POST':
        return views.add_image(request)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])


def demux_image(request, image_id):
    if request.method == 'GET':
        return views.get_image(request, image_id)
    elif request.method == 'HEAD':
        return views.get_image_meta(request, image_id)
    elif request.method == 'PUT':
        return views.update_image(request, image_id)
    else:
        return HttpResponseNotAllowed(['GET', 'HEAD', 'PUT'])


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


urlpatterns = patterns('',
    (r'^images/$', demux),
    (r'^images/detail$', views.list_public_images, {'detail': True}),
    (r'^images/([\w-]+)$', demux_image),
    (r'^images/([\w-]+)/members$', demux_image_members),
    (r'^images/([\w-]+)/members/([\w@._-]+)$', demux_members),
    (r'^shared-images/$', views.list_shared_images),
    (r'^shared-images/detail', views.list_shared_images, {'detail': True}),
    (r'^shared-images/([\w@._-]+)$', views.list_shared_images_with)
)

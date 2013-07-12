# Copyright 2011-2013 GRNET S.A. All rights reserved.
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
from django.http import HttpResponse
from django.utils import simplejson as json
from snf_django.lib import api


from logging import getLogger
log = getLogger(__name__)

urlpatterns = patterns(
    'synnefo.api.extensions',
    (r'^(?:/|.json|.xml)?$', 'demux'),
    (r'^/([\w-]+)(?:/|.json|.xml)?$', 'demux_extension'),
)


def demux(request):
    if request.method == 'GET':
        return list_extensions(request)
    else:
        return api.api_method_not_allowed(request)


def demux_extension(request, extension_alias):
    if request.method == 'GET':
        return get_extension(request, extension_alias)
    else:
        return api.api_method_not_allowed(request)


@api.api_method(http_method='GET', user_required=True, logger=log)
def list_extensions(request, detail=False):
    # Temporary return empty list. This will return the SNF: extension.
    data = json.dumps(dict(extensions=[]))
    return HttpResponse(data, status=200)


@api.api_method(http_method='GET', user_required=True, logger=log)
def get_extension(request, extension_alias):
    return HttpResponse(status=404)

# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

import logging

import urlparse

from django.http import (
    HttpResponseNotFound, HttpResponseRedirect, HttpResponse)
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.utils import simplejson as json

from pithos.api.settings import ASTAKOS_URL

from astakosclient import AstakosClient
from astakosclient.errors import AstakosClientException

logger = logging.getLogger(__name__)

USER_CATALOG_URL = "/astakos/api/user_catalogs"
USER_FEEDBACK_URL = "/astakos/api/feedback"
USER_LOGIN_URL = urlparse.urljoin(ASTAKOS_URL, "login")


def delegate_to_login_service(request):
    url = USER_LOGIN_URL
    if not url:
        return HttpResponseNotFound()

    p = urlparse.urlparse(url)
    if request.is_secure():
        proto = 'https://'
    else:
        proto = 'http://'
    params = dict([(k, v) for k, v in request.GET.items()])
    uri = proto + p.netloc + p.path + '?' + urlencode(params)
    return HttpResponseRedirect(uri)


@csrf_exempt
def delegate_to_feedback_service(request):
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    body = request.raw_post_data
    method = request.method
    astakos = AstakosClient(ASTAKOS_URL, retry=2, use_pool=True, logger=logger)
    try:
        data = astakos._call_astakos(token, USER_FEEDBACK_URL, None, body,
                                     method)
        status = 200
    except AstakosClientException, e:
        status = e.status
        details = json.loads(e.details)
        _, d = details.popitem()
        data = d.get('message')
    return HttpResponse(data, status=status)


@csrf_exempt
def delegate_to_user_catalogs_service(request):
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'content-type': 'application/json'}
    body = request.raw_post_data
    method = request.method
    astakos = AstakosClient(ASTAKOS_URL, retry=2, use_pool=True, logger=logger)
    try:
        data = astakos._call_astakos(token, USER_CATALOG_URL, headers, body,
                                     method)
        data = json.dumps(data)
        status = 200
    except AstakosClientException, e:
        status = e.status
        details = json.loads(e.details)
        _, d = details.popitem()
        data = d.get('message')
    return HttpResponse(data, status=status)

# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings

ASTAKOS_URL = getattr(settings, 'ASTAKOS_URL', None)
USER_QUOTA_URL = urlparse.urljoin(ASTAKOS_URL, "astakos/api/quotas")
RESOURCES_URL = urlparse.urljoin(ASTAKOS_URL, "astakos/api/resources")
USER_CATALOG_URL = urlparse.urljoin(ASTAKOS_URL, "astakos/api/user_catalogs")
USER_FEEDBACK_URL = urlparse.urljoin(ASTAKOS_URL, "astakos/api/feedback")

from objpool.http import PooledHTTPConnection

logger = logging.getLogger(__name__)


def proxy(request, url, headers={}, body=None):
    p = urlparse.urlparse(url)

    kwargs = {}
    kwargs['headers'] = headers
    kwargs['headers'].update(request.META)
    kwargs['body'] = body
    kwargs['headers'].setdefault('content-type', 'application/json')
    kwargs['headers'].setdefault('content-length', len(body) if body else 0)

    with PooledHTTPConnection(p.netloc, p.scheme) as conn:
        conn.request(request.method, p.path + '?' + p.query, **kwargs)
        response = conn.getresponse()
        length = response.getheader('content-length', None)
        data = response.read(length)
        status = int(response.status)
        return HttpResponse(data, status=status)


@csrf_exempt
def delegate_to_resources_service(request):
    logger.debug("Delegate resources request to %s" % RESOURCES_URL)
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'X-Auth-Token': token}
    return proxy(request, RESOURCES_URL, headers=headers,
                 body=request.raw_post_data)


@csrf_exempt
def delegate_to_user_quota_service(request):
    logger.debug("Delegate quotas request to %s" % USER_QUOTA_URL)
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'X-Auth-Token': token}
    return proxy(request, USER_QUOTA_URL, headers=headers,
                 body=request.raw_post_data)


@csrf_exempt
def delegate_to_feedback_service(request):
    logger.debug("Delegate feedback request to %s" % USER_FEEDBACK_URL)
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'X-Auth-Token': token}
    return proxy(request, USER_FEEDBACK_URL, headers=headers,
                 body=request.raw_post_data)


@csrf_exempt
def delegate_to_user_catalogs_service(request):
    token = request.META.get('HTTP_X_AUTH_TOKEN')
    headers = {'X-Auth-Token': token, 'content-type': 'application/json'}
    return proxy(request, USER_CATALOG_URL, headers=headers,
                 body=request.raw_post_data)

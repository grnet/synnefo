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

# Decorator for API methods, using common utils.api_method decorator.
# It is used for 'get_services' and 'get_menu' methods that do not
# require any sort of authentication

from functools import partial

from django.http import HttpResponse
from django.utils import simplejson as json
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth.models import User

from snf_django.lib import api
from astakos.im.models import Service
from astakos.im import settings

import logging
logger = logging.getLogger(__name__)

absolute = lambda request, url: request.build_absolute_uri(url)

api_method = partial(api.api_method, user_required=False,
                     token_required=False, logger=logger)


@api_method(http_method=None)
def get_services(request):
    callback = request.GET.get('callback', None)
    mimetype = 'application/json'
    data = json.dumps(Service.catalog().values())

    if callback:
        # Consume session messages. When get_services is loaded from an astakos
        # page, messages should have already been consumed in the html
        # response. When get_services is loaded from another domain/service we
        # consume them here so that no stale messages to appear if user visits
        # an astakos view later on.
        # TODO: messages could be served to other services/sites in the dict
        # response of get_services and/or get_menu. Services could handle those
        # messages respectively.
        messages_list = list(messages.get_messages(request))
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)

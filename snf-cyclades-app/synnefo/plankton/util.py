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

from functools import wraps
from logging import getLogger
from traceback import format_exc

from django.conf import settings
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseServerError, HttpResponseForbidden)

from snf_django.lib.api import faults
from snf_django.lib.astakos import get_user
from synnefo.plankton.backend import (ImageBackend, BackendException,
                                      NotAllowedError)

log = getLogger('synnefo.plankton')


def plankton_method(method):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                get_user(request, settings.ASTAKOS_URL)
                if not request.user_uniq:
                    return HttpResponse(status=401)
                if request.method != method:
                    return HttpResponse(status=405)
                request.backend = ImageBackend(request.user_uniq)
                return func(request, *args, **kwargs)
            except (AssertionError, BackendException) as e:
                message = e.args[0] if e.args else ''
                return HttpResponseBadRequest(message)
            except NotAllowedError:
                return HttpResponseForbidden()
            except faults.Fault, fault:
                return HttpResponse(status=fault.code)
            except Exception as e:
                if settings.DEBUG:
                    message = format_exc(e)
                else:
                    message = ''
                log.exception(e)
                return HttpResponseServerError(message)
            finally:
                if hasattr(request, 'backend'):
                    request.backend.close()
        return wrapper
    return decorator

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

from django.conf import settings
from django.views.debug import SafeExceptionReporterFilter
from django.http import HttpRequest, build_request_repr

HIDDEN_ALL = settings.HIDDEN_COOKIES + settings.HIDDEN_HEADERS
CLEANSED_SUBSTITUTE = u'********************'


class SynnefoExceptionReporterFilter(SafeExceptionReporterFilter):
    def is_active(self, request):
        # Ignore DEBUG setting. Always active filtering!
        return True

    def get_traceback_frame_variables(self, request, tb_frame):
        sensitive_variables = HIDDEN_ALL
        cleansed = []
        if self.is_active(request) and sensitive_variables:
            if sensitive_variables == '__ALL__':
                # Cleanse all variables
                for name, value in tb_frame.f_locals.items():
                    cleansed.append((name, CLEANSED_SUBSTITUTE))
                return cleansed
            else:
                # Cleanse specified variables
                for name, value in tb_frame.f_locals.items():
                    if name in sensitive_variables:
                        value = CLEANSED_SUBSTITUTE
                    elif isinstance(value, HttpRequest):
                        # Cleanse the request's POST parameters.
                        value = self.get_request_repr(value)
                    cleansed.append((name, value))
                return cleansed
        else:
            # Potentially cleanse only the request if it's one of the frame
            # variables.
            for name, value in tb_frame.f_locals.items():
                if isinstance(value, HttpRequest):
                    # Cleanse the request's POST parameters.
                    value = self.get_request_repr(value)
                cleansed.append((name, value))
            return cleansed

    def get_request_repr(self, request):
        if request is None:
            return repr(None)
        else:
            # Use custom method method to build the request representation
            # where all sensitive values will be cleansed
            _repr = self.build_request_repr(request)
            # Respect max mail size
            if len(_repr) > settings.MAIL_MAX_LEN:
                _repr += "Mail size over limit (truncated)\n\n" + _repr
            return _repr[:settings.MAIL_MAX_LEN]

    def build_request_repr(self, request):
        cleansed = {}
        for fields in ["GET", "POST", "COOKIES", "META"]:
            _cleansed = getattr(request, fields).copy()
            for key in _cleansed.keys():
                for hidden in HIDDEN_ALL:
                    if hidden in key:
                        _cleansed[key] = CLEANSED_SUBSTITUTE
            cleansed[fields] = _cleansed
        return build_request_repr(request,
                                  GET_override=cleansed["GET"],
                                  POST_override=cleansed["POST"],
                                  COOKIES_override=cleansed["COOKIES"],
                                  META_override=cleansed["META"])

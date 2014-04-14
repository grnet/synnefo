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

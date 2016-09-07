# Copyright (C) 2010-2016 GRNET S.A.
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
from raven.processors import Processor
from synnefo.webproject.cleanse_utils import (
    cleanse_request,
    cleanse_jsonstr,
    cleanse_formstr,
    cleanse_str,
    cleanse,
    CLEANSED_SUBSTITUTE
)

HIDDEN_COOKIES = settings.HIDDEN_COOKIES
HIDDEN_HEADERS = settings.HIDDEN_HEADERS
HIDDEN_STACKVARS = settings.HIDDEN_STACKVARS

HIDDEN_ALL = settings.HIDDEN_COOKIES + settings.HIDDEN_HEADERS


class SynnefoFilterProcessor(Processor):
    """
    Filter out Synnefo sensitive values
    """

    def is_active(self):
        # possibly we could deactivate this with a setting
        return True


    def filter_extra(self, data):
        if not self.is_active():
            return

        request = data.get('request', None)
        if request is not None:
            data['request'] = cleanse_request(request, HIDDEN_COOKIES,
                                              HIDDEN_ALL)

        return data


    def filter_http(self, data):
        if not self.is_active():
            return

        # query_string should not contain any sensitive information

        if data['method'] != 'GET':
            if data['data']:
                content_type =  data['headers'].get('Content-Type', None)
                if content_type is None:
                    reason = "No content type found"
                    data['data'] = cleanse_str(data['data'], HIDDEN_ALL,
                                               case=False, reason=reason)
                elif content_type.lower() == 'application/json':
                    data['data'] = cleanse_jsonstr(data['data'], HIDDEN_ALL,
                                                   case=False)
                elif content_type.lower() == 'application/x-www-form-urlencoded':
                    data['data'] = cleanse_formstr(data['data'], HIDDEN_ALL,
                                                   case=False)
                else:
                    reason = "Unknown content type: '%s'" % content_type
                    data['data'] = cleanse_str(data['data'], HIDDEN_ALL,
                                               case=False, reason=reason)

        data['cookies'] = cleanse(data['cookies'], HIDDEN_COOKIES, case=False)
        # these are not wsgi headers starting with 'HTTP_'
        data['headers'] = cleanse(data['headers'], HIDDEN_HEADERS, case=False)


    def filter_stacktrace(self, stacktrace):
        if not self.is_active():
            return

        for frame in stacktrace.get('frames', []):
            if 'vars' not in frame:
                continue
            # here all vars are already transformed (serialized) to strings
            frame['vars'] = cleanse(frame['vars'], HIDDEN_STACKVARS,
                                    case=False)


class DispatcherFilterProcessor(Processor):
    """
    Filter out Synnefo sensitive values
    """

    def is_active(self):
        # possibly we could deactivate this with a setting
        return True


    def filter_stacktrace(self, stacktrace):
        if not self.is_active():
            return

        for frame in stacktrace.get('frames', []):
            if 'vars' not in frame:
                continue
            frame['vars'] = cleanse(frame['vars'], '__ALL__', case=False)

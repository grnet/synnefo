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

from django.views.decorators.csrf import csrf_exempt

from snf_django.lib import api

from .util import (
    get_uuid_displayname_catalogs as get_uuid_displayname_catalogs_util,
    send_feedback as send_feedback_util,
    component_from_token)

import logging
logger = logging.getLogger(__name__)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False,
                logger=logger)
@component_from_token  # Authenticate service !!
def get_uuid_displayname_catalogs(request):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    return get_uuid_displayname_catalogs_util(request, user_call=False)


@csrf_exempt
@api.api_method(http_method='POST', token_required=True, user_required=False,
                logger=logger)
@component_from_token  # Authenticate service !!
def send_feedback(request, email_template_name='im/feedback_mail.txt'):
    # Normal Response Codes: 200
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    return send_feedback_util(request, email_template_name)

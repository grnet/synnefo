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

from pithos.api.functions import _object_read
from pithos.api.util import api_method, view_method

import logging
logger = logging.getLogger(__name__)


@csrf_exempt
def object_demux(request, v_account, v_container, v_object):
    if request.method == 'GET':
        return object_read(request, v_account, v_container, v_object)
    else:
        return api.api_method_not_allowed(request, allowed_methods=['GET'])


@view_method()
def object_read(request, v_account, v_container, v_object):
    return _object_read(request, v_account, v_container, v_object)

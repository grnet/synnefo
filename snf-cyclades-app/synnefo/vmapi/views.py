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

from logging import getLogger

from django.http import Http404, HttpResponse

from synnefo.vmapi import backend, get_key
from synnefo.vmapi import settings

log = getLogger('synnefo.vmapi')


def server_params(request, uuid):
    if not uuid:
        raise Http404

    cache_key = get_key(uuid)
    params = backend.get(cache_key)
    if not params:
        log.error('Request vmapi params key not found: %s', cache_key)
        raise Http404

    if settings.RESET_PARAMS:
        backend.set(cache_key, None)

    return HttpResponse(params, content_type="application/json")

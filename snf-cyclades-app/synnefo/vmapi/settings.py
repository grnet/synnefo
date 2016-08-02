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
from synnefo.cyclades_settings import BASE_URL, BASE_HOST, BASE_PATH

VMAPI_CACHE = settings.VMAPI_CACHE
settings.CACHES['vmapi'] = VMAPI_CACHE

CACHE_KEY_PREFIX = VMAPI_CACHE.get("KEY_PREFIX", "")


RESET_PARAMS = settings.VMAPI_RESET_PARAMS
BASE_HOST = getattr(settings, 'VMAPI_BASE_HOST', BASE_HOST)

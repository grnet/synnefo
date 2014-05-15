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
from synnefo.cyclades_settings import BASE_URL, BASE_HOST, BASE_PATH

CACHE_BACKEND = getattr(settings, 'VMAPI_CACHE_BACKEND',
                        settings.CACHE_BACKEND)
CACHE_KEY_PREFIX = getattr(settings, 'VMAPI_CACHE_KEY_PREFIX',
                           'vmapi')
RESET_PARAMS = getattr(settings, 'VMAPI_RESET_PARAMS', True)
BASE_HOST = getattr(settings, 'VMAPI_BASE_HOST', BASE_HOST)

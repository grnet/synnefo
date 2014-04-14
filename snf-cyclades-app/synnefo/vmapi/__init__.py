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

from uuid import uuid4

from django.core.cache import get_cache
from django.core import signals

from synnefo.vmapi.settings import CACHE_KEY_PREFIX, CACHE_BACKEND


def get_uuid():
    return str(uuid4())


def get_key(*args):
    args = map(str, filter(bool, list(args)))
    args.insert(0, CACHE_KEY_PREFIX)
    return "_".join(args)

# initialize serverparams cache backend
backend = get_cache(CACHE_BACKEND)

# Some caches -- pythont-memcached in particular -- need to do a cleanup at the
# end of a request cycle. If the cache provides a close() method, wire it up
# here.
if hasattr(backend, 'close'):
    signals.request_finished.connect(backend.close)

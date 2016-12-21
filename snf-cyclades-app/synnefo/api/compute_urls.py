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

from django.conf.urls import include, patterns

from snf_django.lib.api import api_endpoint_not_found

from synnefo.api import (servers, flavors, images, extensions, keypairs,
                         floating_ips)
from synnefo.api.compute_versions import versions_list, version_details

#
# The OpenStack Compute API v2.0
#
compute_api20_patterns = patterns(
    '',
    (r'^servers', include(servers)),
    (r'^flavors', include(flavors)),
    (r'^images', include(images)),
    (r'^extensions', include(extensions)),
    (r'^os-keypairs', include(keypairs)),
    (r'^os-floating-ips', include(floating_ips.compute_urlpatterns))
)


urlpatterns = patterns(
    '',
    (r'^(?:.json|.xml|.atom)?$', versions_list),
    (r'^v2.0/(?:.json|.xml|.atom)?$', version_details,
        {'api_version': 'v1.1'}),
    (r'^v2.0/', include(compute_api20_patterns)),
    (r'^.*', api_endpoint_not_found),
)

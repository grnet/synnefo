# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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

from django.conf.urls import include, patterns

from snf_django.lib.api import api_endpoint_not_found
from synnefo.api import (servers, flavors, images, networks, extensions,
                         ports, floating_ips, subnets)
from synnefo.api.versions import versions_list, version_details


#
# The OpenStack Compute API v2.0
#
api20_patterns = patterns(
    '',
    (r'^servers', include(servers)),
    (r'^flavors', include(flavors)),
    (r'^images', include(images)),
    (r'^networks', include(networks)),
    (r'^ports', include(ports)),
    (r'^subnets', include(subnets)),
    (r'^extensions', include(extensions)),
    (r'^os-floating-ips', include(floating_ips.ips_urlpatterns)),
    (r'^os-floating-ip-pools', include(floating_ips.pools_urlpatterns)),
)


urlpatterns = patterns(
    '',
    (r'^(?:.json|.xml|.atom)?$', versions_list),
    (r'^v2.0/(?:.json|.xml|.atom)?$', version_details,
        {'api_version': 'v1.1'}),
    (r'^v2.0/', include(api20_patterns)),
    (r'^.*', api_endpoint_not_found),
)

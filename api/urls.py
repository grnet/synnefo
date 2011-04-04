#
# Copyright (c) 2010 Greek Research and Technology Network
#

from django.conf.urls.defaults import include, patterns

from synnefo.api import servers, flavors, images
from synnefo.api.common import not_found
from synnefo.api.versions import versions_list, version_details


#
# The OpenStack Compute API v1.1
#
api11_patterns = patterns('',
    (r'^servers', include(servers)),
    (r'^flavors', include(flavors)),
    (r'^images', include(images)),
)


urlpatterns = patterns('',
    (r'^(?:.json|.xml|.atom)?$', versions_list),
    (r'^v1.1/(?:.json|.xml|.atom)?$', version_details, {'api_version': 'v1.1'}),
    (r'^v1.1/', include(api11_patterns)),
    (r'^.+', not_found),
)

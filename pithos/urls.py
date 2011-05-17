#
# Copyright (c) 2011 Greek Research and Technology Network
#

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^v1$', include('pithos.api.urls')),
    (r'^v1/', include('pithos.api.urls'))
)

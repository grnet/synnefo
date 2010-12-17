# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^auth/api/', include('synnefo.auth.urls')),
    (r'^api/', include('synnefo.api.urls')),
    (r'^', include('synnefo.ui.urls')),
)

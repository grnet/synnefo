# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2011 Greek Research and Technology Network
#

from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^v1/', include('pithos.api.urls')),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls))
)

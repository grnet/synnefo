# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^lang/$', 'synnefo.ui.i18n.set_language'),
    (r'^auth/api/', include('synnefo.auth.urls')),
    (r'^api/', include('synnefo.api.urls')),
    (r'^', include('synnefo.ui.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^invitation/', include('synnefo.invitations.urls')),
)

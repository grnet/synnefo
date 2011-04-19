# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright (c) 2011 Greek Research and Technology Network
#

from django.conf.urls.defaults import *

# TODO: This only works when in this order.
# TODO: Define which characters can be used in each "path" component.
urlpatterns = patterns('pithos.api.functions',
	(r'^$', 'authenticate'),
	(r'^(?P<v_account>.+?)/(?P<v_container>.+?)/(?P<v_object>.+?)$', 'object_demux'),
	(r'^(?P<v_account>.+?)/(?P<v_container>.+?)$', 'container_demux'),
	(r'^(?P<v_account>.+?)$', 'account_demux')
)

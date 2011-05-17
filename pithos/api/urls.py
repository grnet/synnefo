from django.conf.urls.defaults import *

# TODO: This only works when in this order.
urlpatterns = patterns('pithos.api.functions',
    (r'^$', 'top_demux'),
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)/(?P<v_object>.+?)$', 'object_demux'),
    (r'^(?P<v_account>.+?)/(?P<v_container>.+?)$', 'container_demux'),
    (r'^(?P<v_account>.+?)$', 'account_demux')
)

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^token', 'synnefo.helpdesk.helpdesk.get_tmp_token'),
    (r'^$', 'synnefo.helpdesk.helpdesk.index'),
)

from django.conf.urls.defaults import *
import os

urlpatterns = patterns('',
    (r'^$', 'synnefo.helpdesk.helpdesk.index'),
    (r'^/token$', 'synnefo.helpdesk.helpdesk.get_tmp_token'),
)

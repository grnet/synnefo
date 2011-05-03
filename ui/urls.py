from django.conf.urls.defaults import *
import os


urlpatterns = patterns('',
    (r'^$', 'synnefo.ui.views.home'),
    (r'^machines$', 'synnefo.ui.views.machines'),
    (r'^machines/standard$', 'synnefo.ui.views.machines_standard'),
    (r'^machines/list$', 'synnefo.ui.views.machines_list'),
    (r'^machines/console$', 'synnefo.ui.views.machine_console'),
    (r'^disks$', 'synnefo.ui.views.disks'),
    (r'^images$', 'synnefo.ui.views.images'),
    (r'^networks$', 'synnefo.ui.views.networks'),
    (r'^files$', 'synnefo.ui.views.files'),
    (r'^desktops$', 'synnefo.ui.views.desktops'),
    (r'^datetime$', 'synnefo.ui.views.current_datetime'),
    (r'^apps$', 'synnefo.ui.views.apps'),
    (r'^static/(.*)$', 'django.views.static.serve',
     {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
)

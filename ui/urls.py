from django.conf.urls.defaults import *
import os

urlpatterns = patterns('',
    url(r'^$', 'synnefo.ui.views.home', name='index'),
    url(r'^machines$', 'synnefo.ui.views.machines', name='machines'),
    url(r'^machines/standard$', 'synnefo.ui.views.machines_icon', name='machines-standard'),
    url(r'^machines/list$', 'synnefo.ui.views.machines_list', name='machines-list'),
    url(r'^machines/single$', 'synnefo.ui.views.machines_single', name='machines-single'),
    url(r'^machines/console$', 'synnefo.ui.views.machines_console', name='machines-console'),
    url(r'^disks$', 'synnefo.ui.views.disks', name='disks'),
    url(r'^images$', 'synnefo.ui.views.images', name='images'),
    url(r'^networks$', 'synnefo.ui.views.networks', name='networks'),
    url(r'^files$', 'synnefo.ui.views.files', name='files'),
    url(r'^desktops$', 'synnefo.ui.views.desktops', name='desktop'),
    url(r'^apps$', 'synnefo.ui.views.apps', name='apps'),
    url(r'^static/(.*)$', 'django.views.static.serve',
    {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
)



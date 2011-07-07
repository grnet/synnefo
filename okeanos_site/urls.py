import os
from synnefo.urls import *

urlpatterns += patterns('',
    url(r'^intro$', 'synnefo.okeanos_site.views.intro', name='okeanos_intro'),
    url(r'^okeanos$', 'synnefo.okeanos_site.views.index', name='okeanos_index'),
    url(r'^okeanos_static/(.*)$', 'django.views.static.serve',
    {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
)


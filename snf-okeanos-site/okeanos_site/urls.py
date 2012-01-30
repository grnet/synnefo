import os

from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',

    # change app url from root (/) to (/ui)
    url(r'^ui$', 'synnefo.ui.views.home', name='index'),

    # intro page is now the root
    url(r'^$', 'okeanos_site.views.intro', name='okeanos_intro'),
    # intro view also as /intro to avoid appending root (/) to the AAI_SKIP_LIST
    url(r'^intro$', 'okeanos_site.views.intro', name='okeanos_intro'),

    # video/info page
    url(r'^about$', 'okeanos_site.views.index', name='okeanos_index'),
)

urlpatterns += patterns('',
    url(r'^okeanos_static/(.*)$', 'django.views.static.serve',
    {'document_root': os.path.join(os.path.dirname(__file__), 'static/okeanos_static')}),
)

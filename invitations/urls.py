from django.conf.urls.defaults import *
import os

urlpatterns = patterns('',
    (r'^$', 'synnefo.invitations.invitations.inv_demux'),
    (r'^static/(.*)$', 'django.views.static.serve', {'document_root': os.path.join(os.path.dirname(__file__), 'static')}),
    (r'^login/?$', 'synnefo.invitations.invitations.login')
)

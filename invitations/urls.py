from django.conf.urls.defaults import patterns


urlpatterns = patterns('synnefo.invitations.invitations',
    (r'^$', 'inv_demux')
)

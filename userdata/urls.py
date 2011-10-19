from django.conf.urls.defaults import *
from synnefo.userdata import views

urlpatterns = patterns('',
    url(r'^keys/$', views.PublicKeyPairCollectionView.as_view('keys_resource'),
        name='keys_collection'),
    url(r'^keys/(?P<id>\d+)/$',
    views.PublicKeyPairResourceView.as_view('keys_resource'),
        name="keys_resource"),
)

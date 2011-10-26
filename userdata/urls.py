from django.conf.urls.defaults import *
from synnefo.userdata import views

urlpatterns = patterns('',
    url(r'^keys$', views.PublicKeyPairCollectionView.as_view('keys_resource'),
        name='keys_collection'),
    url(r'^keys/(?P<id>\d+)',
    views.PublicKeyPairResourceView.as_view('keys_resource'),
        name="keys_resource"),
    url(r'keys/generate', views.generate_key_pair, name="generate_public_key"),
    url(r'keys/download', views.download_private_key, name="download_public_key")
)

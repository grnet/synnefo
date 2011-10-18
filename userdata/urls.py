from django.conf.urls.defaults import *
from synnefo.userdata import views

urlpatterns = patterns('',
    (r'^keys/$', views.PublicKeyPairCollectionView.as_view()),
    (r'^keys/(?P<id>\d+)/$', views.PublicKeyPairResourceView.as_view()),
)

from django import http
from django.template import RequestContext, loader
from django.utils import simplejson as json

from synnefo.userdata import rest
from synnefo.userdata.models import PublicKeyPair

class PublicKeyPairResourceView(rest.UserResourceView):
    model = PublicKeyPair
    exclude_fields = ["user"]

class PublicKeyPairCollectionView(rest.UserCollectionView):
    model = PublicKeyPair
    exclude_fields = ["user"]

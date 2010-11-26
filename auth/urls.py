# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.conf.urls.defaults import *
from piston.resource import Resource
from synnefo.auth.handlers import *

auth_handler = Resource(AuthHandler)

urlpatterns = patterns('',
    (r'^v1.0', auth_handler),
)

# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright (c) 2011 Greek Research and Technology Network
#

from api.models import Container, Object, Metadata
from django.contrib import admin

admin.site.register(Container)
admin.site.register(Object)
admin.site.register(Metadata)
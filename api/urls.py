# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.conf.urls.defaults import *
from piston.resource import Resource
from synnefo.api.handlers import *
from synnefo.api.authentication import TokenAuthentication

auth = TokenAuthentication()

limit_handler = Resource(LimitHandler, auth)
server_handler = Resource(ServerHandler, auth)
server_address_handler = Resource(ServerAddressHandler, auth)
server_actions_handler = Resource(ServerActionHandler, auth)
server_backup_handler = Resource(ServerBackupHandler, auth)
flavor_handler = Resource(FlavorHandler, auth)
image_handler = Resource(ImageHandler, auth)
shared_ip_group_handler = Resource(SharedIPGroupHandler, auth)

v10patterns = patterns('',
    url(r'^limits$', limit_handler),
    url(r'^servers/(?P<id>[^/]+)?$', server_handler),
    url(r'^servers/(?P<id>[^/]+)/action$', server_actions_handler),
    url(r'^servers/(?P<id>[^/]+)/ips$', server_address_handler),
    url(r'^servers/(?P<id>[^/]+)/ips/private$', server_address_handler),
    url(r'^servers/(?P<id>[^/]+)/ips/public/(?P<address>[^/]+)$', server_address_handler),
    url(r'^servers/(?P<id>[^/]+)/backup_schedule', server_backup_handler),
    url(r'^flavors/(?P<id>[^/]+)?$', flavor_handler),
    url(r'^images/(?P<id>[^/]+)?$', image_handler),
    url(r'^shared_ip_groups/(?P<id>[^/]+)?$', shared_ip_group_handler),
)

version_handler = Resource(VersionHandler)

urlpatterns = patterns('',
    url(r'^(?P<number>[^/]+)/$', version_handler),
    url(r'^/?$', version_handler),
    (r'^v1.0/', include(v10patterns)),
)

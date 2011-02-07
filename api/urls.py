# vim: ts=4 sts=4 et ai sw=4 fileencoding=utf-8
#
# Copyright © 2010 Greek Research and Technology Network
#

from django.conf.urls.defaults import *
from synnefo.helpers import url_with_format
from synnefo.api.resource import Resource
from synnefo.api.handlers import *
from synnefo.api.authentication import TokenAuthentication
from synnefo.api.faults import fault

auth = TokenAuthentication()

def notFound(request):
    return fault.itemNotFound.response

limit_handler = Resource(LimitHandler, auth)
server_handler = Resource(ServerHandler, auth)
server_address_handler = Resource(ServerAddressHandler, auth)
server_actions_handler = Resource(ServerActionHandler, auth)
server_backup_handler = Resource(ServerBackupHandler, auth)
flavor_handler = Resource(FlavorHandler, auth)
image_handler = Resource(ImageHandler, auth)
shared_ip_group_handler = Resource(SharedIPGroupHandler, auth)
virtual_machine_group_handler = Resource(VirtualMachineGroupHandler, auth)

def url_with_format(regex, *args, **kwargs):
    if regex[-1] == '$':
        regex = regex[:-1]
    regex = regex + r'(\.(?P<emitter_format>json|xml))?$'
    return url(regex, *args, **kwargs)

v10patterns = patterns('',
    url_with_format(r'^limits$', limit_handler),
    url_with_format(r'^servers$', server_handler),
    url_with_format(r'^servers/(?P<id>[^/]+)$', server_handler),
    url_with_format(r'^servers/(?P<id>[^/]+)/action$', server_actions_handler),
    url_with_format(r'^servers/(?P<id>[^/]+)/ips$', server_address_handler),
    url_with_format(r'^servers/(?P<id>[^/]+)/ips/private$', server_address_handler),
    url_with_format(r'^servers/(?P<id>[^/]+)/ips/public/(?P<address>[^/]+)$', server_address_handler),
    url_with_format(r'^servers/(?P<id>[^/]+)/backup_schedule', server_backup_handler),
    url_with_format(r'^flavors$', flavor_handler),
    url_with_format(r'^flavors/(?P<id>[^/]+)$', flavor_handler),
    url_with_format(r'^images$', image_handler),
    url_with_format(r'^images/(?P<id>[^/]+)$', image_handler),
    url_with_format(r'^shared_ip_groups$', shared_ip_group_handler),
    url_with_format(r'^shared_ip_groups/(?P<id>[^/]+)$', shared_ip_group_handler),
    url_with_format(r'^groups$', virtual_machine_group_handler),
    url_with_format(r'^groups/(?P<id>[^/]+)$', virtual_machine_group_handler),
    url(r'^.+', notFound), # catch-all
)

version_handler = Resource(VersionHandler)

urlpatterns = patterns('',
    url_with_format(r'^(?P<number>[^/]+)/?$', version_handler),
    url(r'^$', version_handler),
    url(r'^v1.0/', include(v10patterns)),
    url(r'^.+', notFound), # catch-all
)

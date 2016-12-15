# Copyright (C) 2010-2016 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from copy import deepcopy
from synnefo.lib import join_urls
from urlparse import urlparse


def fill_endpoints(services, base_url):
    for name, service in services.iteritems():
        prefix = service['prefix']
        endpoints = service['endpoints']
        for endpoint in endpoints:
            try:
                expose_version = endpoint['SNF:exposeVersion']
            except KeyError:
                endpoint['SNF:exposeVersion'] = expose_version = True
            version = endpoint['versionId'] if expose_version else ""
            publicURL = endpoint['publicURL']
            if publicURL is not None:
                continue

            publicURL = join_urls(base_url, prefix, version).rstrip('/')
            endpoint['publicURL'] = publicURL


def filter_public(services):
    public_services = {}
    for name, service in services.iteritems():
        if service.get('public', False):
            public_services[name] = deepcopy(service)
    return public_services


def get_versioned_public_url(endpoint):
    version = endpoint['versionId']
    expose_version = endpoint.get('SNF:exposeVersion', True)
    publicURL = endpoint['publicURL']
    if not expose_version:
        publicURL = join_urls(publicURL, version).rstrip('/')
    return publicURL


def get_public_endpoint(services, service_type, version=None):
    found_endpoints = {}
    for service_name, service in services.iteritems():
        if service_type != service['type']:
            continue

        for endpoint in service['endpoints']:
            endpoint_version = endpoint['versionId']
            if version is not None:
                if version != endpoint_version:
                    continue
            found_endpoints[endpoint_version] = endpoint

    if not found_endpoints:
        m = "No endpoint found for service type '{0}'".format(service_type)
        if version is not None:
            m += " and version '{0}'".format(version)
        raise ValueError(m)

    selected = sorted(found_endpoints.keys())[-1]
    return get_versioned_public_url(found_endpoints[selected])


def get_service_path(services, service_type, version=None):
    service_url = get_public_endpoint(services, service_type, version=version)
    return urlparse(service_url).path.rstrip('/')

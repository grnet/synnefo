# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from synnefo.util import units
from astakos.im.models import Resource, Service, Endpoint, EndpointData
from astakos.im import quotas
import logging

logger = logging.getLogger(__name__)

main_fields = ['desc', 'unit']
config_fields = ['ui_visible', 'api_visible']


class RegisterException(Exception):
    pass


def different_component(service, resource):
    try:
        registered_for = Service.objects.get(name=resource.service_origin)
        return registered_for.component != service.component
    except Service.DoesNotExist:
        return False


def add_resource(resource_dict):
    name = resource_dict.get('name')
    service_type = resource_dict.get('service_type')
    service_origin = resource_dict.get('service_origin')
    if not name or not service_type or not service_origin:
        raise RegisterException("Malformed resource dict.")

    try:
        service = Service.objects.get(name=service_origin)
    except Service.DoesNotExist:
        m = "There is no service %s." % service_origin
        raise RegisterException(m)

    try:
        r = Resource.objects.select_for_update().get(name=name)
        exists = True
        if r.service_type != service_type and \
                different_component(service, r):
            m = ("There already exists a resource named %s with service "
                 "type %s." % (name, r.service_type))
            raise RegisterException(m)
        if r.service_origin != service_origin and \
                different_component(service, r):
            m = ("There already exists a resource named %s registered for "
                 "service %s." % (name, r.service_origin))
            raise RegisterException(m)
        r.service_origin = service_origin
        r.service_type = service_type
    except Resource.DoesNotExist:
        r = Resource(name=name,
                     uplimit=units.PRACTICALLY_INFINITE,
                     project_default=units.PRACTICALLY_INFINITE,
                     service_type=service_type,
                     service_origin=service_origin)
        exists = False
        for field in config_fields:
            value = resource_dict.get(field)
            if value is not None:
                setattr(r, field, value)

    for field in main_fields:
        value = resource_dict.get(field)
        if value is not None:
            setattr(r, field, value)

    if r.ui_visible and not r.api_visible:
        m = "Flag 'ui_visible' should entail 'api_visible'."
        raise RegisterException(m)

    r.save()
    if not exists:
        quotas.qh_sync_new_resource(r)

    if exists:
        logger.info("Updated resource %s." % (name))
    else:
        logger.info("Added resource %s." % (name))
    return r, exists


def update_base_default(resource, base_default):
    old_base_default = resource.uplimit
    if base_default == old_base_default:
        logger.info("Resource %s has base default %s; no need to update."
                    % (resource.name, base_default))
    else:
        resource.uplimit = base_default
        resource.save()
        logger.info("Updated resource %s with base default %s."
                    % (resource.name, base_default))


def update_project_default(resource, project_default):
    old_project_default = resource.project_default
    if project_default == old_project_default:
        logger.info("Resource %s has project default %s; no need to update."
                    % (resource.name, project_default))
    else:
        resource.project_default = project_default
        resource.save()
        logger.info("Updated resource %s with project default %s."
                    % (resource.name, project_default))


def resources_to_dict(resources):
    resource_dict = {}
    for r in resources:
        resource_dict[r.name] = r.get_info()
    return resource_dict


def get_resources(resources=None, services=None):
    if resources is None:
        rs = Resource.objects.all()
    else:
        rs = Resource.objects.filter(name__in=resources)

    if services is not None:
        rs = rs.filter(service__in=services)

    return rs


def get_api_visible_resources(resources=None, services=None):
    rs = get_resources(resources, services)
    return rs.filter(api_visible=True)


def add_endpoint(component, service, endpoint_dict, out=None):
    endpoint = Endpoint.objects.create(service=service)
    for key, value in endpoint_dict.iteritems():
        base_url = component.base_url
        if key == "publicURL" and (base_url is None or
                                   not value.startswith(base_url)):
            warn = out.write if out is not None else logger.warning
            warn("Warning: Endpoint URL '%s' does not start with "
                 "assumed component base URL '%s'.\n" % (value, base_url))
        EndpointData.objects.create(
            endpoint=endpoint, key=key, value=value)


def add_service(component, name, service_type, endpoints, out=None):
    defaults = {'component': component,
                'type': service_type,
                }
    service, created = Service.objects.get_or_create(
        name=name, defaults=defaults)

    if not created:
        if service.component != component:
            m = ("There is already a service named %s registered by %s." %
                 (name, service.component.name))
            raise RegisterException(m)
        service.endpoints.all().delete()
        for key, value in defaults.iteritems():
            setattr(service, key, value)
        service.save()

    for endpoint in endpoints:
        add_endpoint(component, service, endpoint, out=out)

    return not created

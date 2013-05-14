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

from astakos.im.models import Resource
from astakos.im.quotas import qh_add_resource_limit, qh_sync_new_resource
import logging

logger = logging.getLogger(__name__)

fields = ['name', 'desc', 'unit', 'allow_in_projects']


class ResourceException(Exception):
    pass


def add_resource(service, resource_dict):
    name = resource_dict.get('name')
    if not name:
        raise ResourceException("Malformed resource dict.")

    try:
        r = Resource.objects.get_for_update(name=name)
        exists = True
    except Resource.DoesNotExist:
        r = Resource(uplimit=0)
        exists = False

    r.service = service
    for field in fields:
        value = resource_dict.get(field)
        if value is not None:
            setattr(r, field, value)

    r.save()
    if not exists:
        qh_sync_new_resource(r, 0)

    if exists:
        logger.info("Updated resource %s." % (name))
    else:
        logger.info("Added resource %s." % (name))
    return r, exists


def update_resource(resource, uplimit):
    old_uplimit = resource.uplimit
    resource.uplimit = uplimit
    resource.save()

    logger.info("Updated resource %s with limit %s."
                % (resource.name, uplimit))
    diff = uplimit - old_uplimit
    if diff != 0:
        qh_add_resource_limit(resource, diff)


def get_resources(resources=None, services=None):
    if resources is None:
        rs = Resource.objects.all()
    else:
        rs = Resource.objects.filter(name__in=resources)

    if services is not None:
        rs = rs.filter(service__in=services)

    resource_dict = {}
    for r in rs:
        resource_dict[r.full_name()] = r.get_info()

    return resource_dict

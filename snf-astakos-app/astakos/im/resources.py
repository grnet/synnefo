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

from astakos.im.models import Service, Resource
from astakos.im.functions import qh_sync_all_users
from astakos.im.quotas import qh_add_resource_limit, qh_sync_new_resource
import logging

logger = logging.getLogger(__name__)


def add_resource(service, resource, uplimit):
    try:
        s = Service.objects.get(name=service)
    except Service.DoesNotExist:
        raise Exception("Service %s is not registered." % (service))

    name = resource['name']
    try:
        r = Resource.objects.get_for_update(name=name)
        old_uplimit = r.uplimit
    except Resource.DoesNotExist:
        r = Resource()
        old_uplimit = None

    r.uplimit = uplimit
    r.service = service
    for key, value in resource.iteritems():
        setattr(r, key, value)

    r.save()

    if old_uplimit is not None:
        logger.info("Updated resource %s with limit %s." % (name, uplimit))
    else:
        logger.info("Added resource %s with limit %s." % (name, uplimit))

    if old_uplimit is not None:
        diff = uplimit - old_uplimit
        if diff != 0:
            qh_add_resource_limit(name, diff)
    else:
        qh_sync_new_resource(name, uplimit)

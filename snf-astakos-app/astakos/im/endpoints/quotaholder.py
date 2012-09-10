# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

import socket
import logging

from django.utils.translation import ugettext as _

from astakos.im.settings import QUOTA_HOLDER_URL, LOGGING_LEVEL

if QUOTA_HOLDER_URL:
    from commissioning.clients.quotaholder import QuotaholderHTTP

ENTITY_KEY = '1'

logger = logging.getLogger(__name__)


def register_users(users, client=None):
    if not users:
        return

    if not QUOTA_HOLDER_URL:
        return

    c = client or QuotaholderHTTP(QUOTA_HOLDER_URL)
    data = []
    append = data.append
    for user in users:
        try:
            entity = user.email
        except AttributeError:
            continue
        else:
            args = entity, owner, key, ownerkey = (
                entity, 'system', ENTITY_KEY, ''
            )
            append(args)

    if not data:
        return

    rejected = c.create_entity(
        context={},
        create_entity=data,
    )
    msg = _('Create entities: %s - Rejected: %s' % (data, rejected,))
    logger.log(LOGGING_LEVEL, msg)

    created = filter(lambda u: unicode(u.email) not in rejected, users)
    send_quota(created, c)
    return rejected


def send_quota(users, client=None):
    if not users:
        return

    if not QUOTA_HOLDER_URL:
        return

    c = client or QuotaholderHTTP(QUOTA_HOLDER_URL)
    data = []
    append = data.append
    for user in users:
        try:
            entity = user.email
        except AttributeError:
            continue
        else:
            for resource, limit in user.quota.iteritems():
                args = entity, resource, key, quantity, capacity, import_limit, \
                    export_limit, flags = (
                        entity, resource, ENTITY_KEY, '0', str(limit), 0, 0, 0
                    )
                append(args)

    if not data:
        return

    rejected = c.set_quota(context={}, set_quota=data)
    msg = _('Set quota: %s - Rejected: %s' % (data, rejected,))
    logger.log(LOGGING_LEVEL, msg)
    return rejected


def get_quota(users, client=None):
    if not users:
        return

    if not QUOTA_HOLDER_URL:
        return

    c = client or QuotaholderHTTP(QUOTA_HOLDER_URL)
    data = []
    append = data.append
    for user in users:
        try:
            entity = user.email
        except AttributeError:
            continue
        else:
            for r in user.quota.keys():
                args = entity, resource, key = entity, r, ENTITY_KEY
                append(args)

    if not data:
        return

    r = c.get_quota(context={}, get_quota=data)
    msg = _('Get quota: %s' % data)
    logger.log(LOGGING_LEVEL, msg)
    return r

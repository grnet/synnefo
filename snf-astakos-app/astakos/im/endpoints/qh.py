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

import logging
import itertools

from functools import wraps
from collections import namedtuple

from django.utils.translation import ugettext as _

from astakos.im.settings import (
        QUOTAHOLDER_URL, QUOTAHOLDER_TOKEN, LOGGING_LEVEL)

if QUOTAHOLDER_URL:
    from kamaki.clients.quotaholder import QuotaholderClient

ENTITY_KEY = '1'
PRACTICALLY_INF = pow(2, 30)

inf = float('inf')

logger = logging.getLogger(__name__)

inf = float('inf')

clientkey = 'astakos'

_client = None
def get_client():
    global _client
    if _client:
        return _client
    if not QUOTAHOLDER_URL:
        return
    _client = QuotaholderClient(QUOTAHOLDER_URL, token=QUOTAHOLDER_TOKEN)
    return _client

def set_quota(payload):
    c = get_client()
    if not c:
        return
    result = c.set_quota(context={}, clientkey=clientkey, set_quota=payload)
    logger.info('set_quota: %s rejected: %s' % (payload, result))
    return result

def get_quota(user):
    c = get_client()
    if not c:
        return
    payload = []
    append = payload.append
    for r in user.quota.keys():
        append((user.uuid, r, ENTITY_KEY),)
    result = c.get_quota(context={}, clientkey=clientkey, get_quota=payload)
    logger.info('get_quota: %s rejected: %s' % (payload, result))
    return result

def create_entity(payload):
    c = get_client()
    if not c:
        return
    result = c.create_entity(context={}, clientkey=clientkey, create_entity=payload)
    logger.info('create_entity: %s rejected: %s' % (payload, result))
    return result

SetQuotaPayload = namedtuple('SetQuotaPayload', ('holder',
                                                 'resource',
                                                 'key',
                                                 'quantity',
                                                 'capacity',
                                                 'import_limit',
                                                 'export_limit',
                                                 'flags'))

GetQuotaPayload = namedtuple('GetQuotaPayload', ('holder',
                                                 'resource',
                                                 'key'))

CreateEntityPayload = namedtuple('CreateEntityPayload', ('entity',
                                                         'owner',
                                                         'key',
                                                         'ownerkey'))
QuotaLimits = namedtuple('QuotaLimits', ('holder',
                                         'resource',
                                         'capacity',
                                         'import_limit',
                                         'export_limit'))

def register_users(users):
    payload = list(CreateEntityPayload(
                    entity=u.uuid,
                    owner='system',
                    key=ENTITY_KEY,
                    ownerkey='') for u in users)
    rejected = create_entity(payload)
    if not rejected:
        payload = []
        append = payload.append
        for u in users:
            for resource, uplimit in u.quota.iteritems():
                append( SetQuotaPayload(
                                holder=u.uuid,
                                resource=resource,
                                key=ENTITY_KEY,
                                quantity=0,
                                capacity=uplimit if uplimit != inf else None,
                                import_limit=PRACTICALLY_INF,
                                export_limit=PRACTICALLY_INF,
                                flags=0))
        return set_quota(payload)


def register_resources(resources):
    rdata = ((r.service, r) for r in resources)
    services = set(r.service for r in resources)
    payload = list(CreateEntityPayload(
                    entity=service,
                    owner='system',
                    key=ENTITY_KEY,
                    ownerkey='') for service in set(services))
    rejected = create_entity(payload)
    if not rejected:
        payload = list(SetQuotaPayload(
                        holder=resource.service,
                        resource=resource,
                        key=ENTITY_KEY,
                        quantity=PRACTICALLY_INF,
                        capacity=0,
                        import_limit=PRACTICALLY_INF,
                        export_limit=PRACTICALLY_INF,
                        flags=0) for resource in resources)
        return set_quota(payload)

def qh_add_quota(serial, sub_list, add_list):
    if not QUOTAHOLDER_URL:
        return ()

    context = {}
    c = get_client()
    
    sub_quota = []
    sub_append = sub_quota.append
    add_quota = []
    add_append = add_quota.append

    for ql in sub_list:
        args = (ql.holder, ql.resource, ENTITY_KEY,
                0, ql.capacity, ql.import_limit, ql.export_limit)
        sub_append(args)

    for ql in add_list:
        args = (ql.holder, ql.resource, ENTITY_KEY,
                0, ql.capacity, ql.import_limit, ql.export_limit)
        add_append(args)

    result = c.add_quota(context=context,
                         clientkey=clientkey,
                         serial=serial,
                         sub_quota=sub_quota,
                         add_quota=add_quota)

    return result

def qh_query_serials(serials):
    if not QUOTAHOLDER_URL:
        return ()

    context = {}
    c = get_client()
    result = c.query_serials(context=context,
                             clientkey=clientkey,
                             serials=serials)
    return result

def qh_ack_serials(serials):
    if not QUOTAHOLDER_URL:
        return ()

    context = {}
    c = get_client()
    result = c.ack_serials(context=context,
                           clientkey=clientkey,
                           serials=serials)
    return

from datetime import datetime

strptime = datetime.strptime
timefmt = '%Y-%m-%dT%H:%M:%S.%f'

SECOND_RESOLUTION = 1


def total_seconds(timedelta_object):
    return timedelta_object.seconds + timedelta_object.days * 86400


def iter_timeline(timeline, before):
    if not timeline:
        return

    for t in timeline:
        yield t

    t = dict(t)
    t['issue_time'] = before
    yield t


def _usage_units(timeline, after, before, details=0):

    t_total = 0
    uu_total = 0
    t_after = strptime(after, timefmt)
    t_before = strptime(before, timefmt)
    t0 = t_after
    u0 = 0

    for point in iter_timeline(timeline, before):
        issue_time = point['issue_time']

        if issue_time <= after:
            u0 = point['target_allocated_through']
            continue

        t = strptime(issue_time, timefmt) if issue_time <= before else t_before
        t_diff = int(total_seconds(t - t0) * SECOND_RESOLUTION)
        t_total += t_diff
        uu_cost = u0 * t_diff
        uu_total += uu_cost
        t0 = t
        u0 = point['target_allocated_through']

        target = point['target']
        if details:
            yield  (target,
                    point['resource'],
                    point['name'],
                    issue_time,
                    uu_cost,
                    uu_total)

    if not t_total:
        return

    yield  (target,
            'total',
            point['resource'],
            issue_time,
            uu_total / t_total,
            uu_total)


def usage_units(timeline, after, before, details=0):
    return list(_usage_units(timeline, after, before, details=details))


def traffic_units(timeline, after, before, details=0):
    tu_total = 0
    target = None
    issue_time = None

    for point in timeline:
        issue_time = point['issue_time']
        if issue_time <= after:
            continue
        if issue_time > before:
            break

        target = point['target']
        tu = point['target_allocated_through']
        tu_total += tu

        if details:
            yield  (target,
                    point['resource'],
                    point['name'],
                    issue_time,
                    tu,
                    tu_total)

    if not tu_total:
        return

    yield  (target,
            'total',
            point['resource'],
            issue_time,
            tu_total // len(timeline),
            tu_total)


def timeline_charge(entity, resource, after, before, details, charge_type):
    key = '1'
    if charge_type == 'charge_usage':
        charge_units = usage_units
    elif charge_type == 'charge_traffic':
        charge_units = traffic_units
    else:
        m = 'charge type %s not supported' % charge_type
        raise ValueError(m)

    quotaholder = QuotaholderClient(QUOTAHOLDER_URL, token=QUOTAHOLDER_TOKEN)
    timeline = quotaholder.get_timeline(
        context={},
        after=after,
        before=before,
        get_timeline=[[entity, resource, key]])
    cu = charge_units(timeline, after, before, details=details)
    return cu

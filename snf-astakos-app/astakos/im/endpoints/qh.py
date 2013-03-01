# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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

from astakos.quotaholder.callpoint import QuotaholderDjangoDBCallpoint
from synnefo.util.number import strbigdec
from astakos.im.settings import QUOTAHOLDER_POOLSIZE

from astakos.quotaholder.api import QH_PRACTICALLY_INFINITE

logger = logging.getLogger(__name__)

inf = float('inf')

clientkey = 'astakos'

_client = None


def get_client():
    global _client
    if _client:
        return _client
    _client = QuotaholderDjangoDBCallpoint()
    return _client


def set_quota(payload):
    c = get_client()
    if not c:
        return
    if payload == []:
        return []
    result = c.set_quota(context={}, set_quota=payload)
    logger.debug('set_quota: %s rejected: %s' % (payload, result))
    return result


def get_holding(payload):
    c = get_client()
    if not c:
        return
    if payload == []:
        return []
    result = c.get_holding(context={}, get_holding=payload)
    logger.debug('get_holding: %s reply: %s' % (payload, result))
    return result


def qh_get_holdings(users, resources):
    payload = []
    append = payload.append
    for user in users:
        for resource in resources:
            append((user.uuid, resource),)
    result = get_holding(payload)
    return result


def quota_limits_per_user_from_get(lst):
    quotas = {}
    for holder, resource, q, c, imp, exp, ret, rel, flags in lst:
        userquotas = quotas.get(holder, {})
        userquotas[resource] = QuotaValues(quantity=q, capacity=c,
                                           )
        quotas[holder] = userquotas
    return quotas


def quotas_per_user_from_get(lst):
    limits = {}
    counters = {}
    for holder, resource, q, c, imp, exp, ret, rel, flags in lst:
        userlimits = limits.get(holder, {})
        userlimits[resource] = QuotaValues(quantity=q, capacity=c,
                                           )
        limits[holder] = userlimits

        usercounters = counters.get(holder, {})
        usercounters[resource] = QuotaCounters(imported=imp, exported=exp,
                                               returned=ret, released=rel)
        counters[holder] = usercounters
    return limits, counters


def qh_get_quota(users, resources):
    c = get_client()
    if not c:
        return
    payload = []
    append = payload.append
    for user in users:
        for resource in resources:
            append((user.uuid, resource),)

    if payload == []:
        return []
    result = c.get_quota(context={}, get_quota=payload)
    logger.debug('get_quota: %s rejected: %s' % (payload, result))
    return result


def qh_get_quota_limits(users, resources):
    result = qh_get_quota(users, resources)
    return quota_limits_per_user_from_get(result)


def qh_get_quotas(users, resources):
    result = qh_get_quota(users, resources)
    return quotas_per_user_from_get(result)


SetQuotaPayload = namedtuple('SetQuotaPayload', ('holder',
                                                 'resource',
                                                 'quantity',
                                                 'capacity',
                                                 'flags'))

QuotaLimits = namedtuple('QuotaLimits', ('holder',
                                         'resource',
                                         'capacity',
                                         ))

QuotaCounters = namedtuple('QuotaCounters', ('imported',
                                             'exported',
                                             'returned',
                                             'released'))


class QuotaValues(namedtuple('QuotaValues', ('quantity',
                                             'capacity',
                                             ))):
    __slots__ = ()

    def __dir__(self):
            return ['quantity', 'capacity']

    def __str__(self):
        return '\t'.join(['%s=%s' % (f, strbigdec(getattr(self, f)))
                          for f in dir(self)])


def add_quota_values(q1, q2):
    return QuotaValues(
        quantity = q1.quantity + q2.quantity,
        capacity = q1.capacity + q2.capacity,
        )


def register_quotas(quotas):
    if not quotas:
        return

    payload = []
    append = payload.append
    for uuid, userquotas in quotas.iteritems():
        for resource, q in userquotas.iteritems():
            append(SetQuotaPayload(
                    holder=uuid,
                    resource=resource,
                    quantity=q.quantity,
                    capacity=q.capacity,
                    flags=0))
    return set_quota(payload)


def send_quotas(userquotas):
    if not userquotas:
        return

    payload = []
    append = payload.append
    for holder, quotas in userquotas.iteritems():
        for resource, q in quotas.iteritems():
            append(SetQuotaPayload(
                    holder=holder,
                    resource=resource,
                    quantity=q.quantity,
                    capacity=q.capacity,
                    flags=0))
    return set_quota(payload)


def register_resources(resources):

    payload = list(SetQuotaPayload(
            holder=resource.service,
            resource=resource,
            quantity=QH_PRACTICALLY_INFINITE,
            capacity=QH_PRACTICALLY_INFINITE,
            flags=0) for resource in resources)
    return set_quota(payload)


def qh_add_quota(sub_list, add_list):
    context = {}
    c = get_client()

    sub_quota = []
    sub_append = sub_quota.append
    add_quota = []
    add_append = add_quota.append

    for ql in sub_list:
        args = (ql.holder, ql.resource,
                0, ql.capacity)
        sub_append(args)

    for ql in add_list:
        args = (ql.holder, ql.resource,
                0, ql.capacity)
        add_append(args)

    result = c.add_quota(context=context,
                         sub_quota=sub_quota,
                         add_quota=add_quota)

    return result


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
            yield (target,
                   point['resource'],
                   point['name'],
                   issue_time,
                   uu_cost,
                   uu_total)

    if not t_total:
        return

    yield (target,
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
            yield (target,
                   point['resource'],
                   point['name'],
                   issue_time,
                   tu,
                   tu_total)

    if not tu_total:
        return

    yield (target,
           'total',
           point['resource'],
           issue_time,
           tu_total // len(timeline),
           tu_total)


def timeline_charge(entity, resource, after, before, details, charge_type):
    if charge_type == 'charge_usage':
        charge_units = usage_units
    elif charge_type == 'charge_traffic':
        charge_units = traffic_units
    else:
        m = 'charge type %s not supported' % charge_type
        raise ValueError(m)

    quotaholder = QuotaholderClient(QUOTAHOLDER_URL, token=QUOTAHOLDER_TOKEN,
                                    poolsize=QUOTAHOLDER_POOLSIZE)
    timeline = quotaholder.get_timeline(
        context={},
        after=after,
        before=before,
        get_timeline=[[entity, resource]])
    cu = charge_units(timeline, after, before, details=details)
    return cu

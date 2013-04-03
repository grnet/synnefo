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

from astakos.quotaholder.callpoint import QuotaholderDjangoDBCallpoint

qh = QuotaholderDjangoDBCallpoint()


def from_holding(holding):
    limit, imported_min, imported_max = holding
    body = {'limit':       limit,
            'used':        imported_min,
            'available':   max(0, limit-imported_max),
            }
    return body


def limits_only(holding):
    limit, imported_min, imported_max = holding
    return limit


def transform_data(holdings, func=None):
    if func is None:
        func = from_holding

    quota = {}
    for (holder, source, resource), value in holdings.iteritems():
        holder_quota = quota.get(holder, {})
        source_quota = holder_quota.get(source, {})
        body = func(value)
        source_quota[resource] = body
        holder_quota[source] = source_quota
        quota[holder] = holder_quota
    return quota


def get_counters(users,  resources=None, sources=None):
    uuids = [user.uuid for user in users]

    counters = qh.get_holder_quota(holders=uuids,
                                   resources=resources,
                                   sources=sources)
    return counters


def get_users_quotas(users, resources=None, sources=None):
    counters = get_counters(users, resources, sources)
    quotas = transform_data(counters)
    return quotas


def get_users_quotas_and_limits(users, resources=None, sources=None):
    counters = get_counters(users, resources, sources)
    quotas = transform_data(counters)
    limits = transform_data(counters, limits_only)
    return quotas, limits


def get_user_quotas(user, resources=None, sources=None):
    quotas = get_users_quotas([user], resources, sources)
    return quotas[user.uuid]


def set_user_quota(quotas):
    qh.set_holder_quota(quotas)

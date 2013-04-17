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

from astakos.im.models import (
    Resource, AstakosUserQuota, AstakosUser,
    Project, ProjectMembership, ProjectResourceGrant, ProjectApplication)
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


def get_service_quotas(service):
    resources = Resource.objects.filter(service=service.name)
    resource_names = [r.name for r in resources]
    counters = qh.get_resource_quota(resource_names)
    return transform_data(counters)


def set_user_quota(quotas):
    qh.set_holder_quota(quotas)


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


def get_default_quota():
    _DEFAULT_QUOTA = {}
    resources = Resource.objects.select_related('service').all()
    for resource in resources:
        capacity = resource.uplimit
        _DEFAULT_QUOTA[resource.full_name()] = capacity

    return _DEFAULT_QUOTA


SYSTEM = 'system'


def initial_quotas(users):
    initial = {}
    default_quotas = get_default_quota()

    for user in users:
        uuid = user.uuid
        source_quota = {SYSTEM: dict(default_quotas)}
        initial[uuid] = source_quota

    objs = AstakosUserQuota.objects.select_related()
    orig_quotas = objs.filter(user__in=users)
    for user_quota in orig_quotas:
        uuid = user_quota.user.uuid
        user_init = initial.get(uuid, {})
        resource = user_quota.resource.full_name()
        user_init[resource] = user_quota.capacity
        initial[uuid] = user_init

    return initial


def get_grant_source(grant):
    return SYSTEM


def users_quotas(users, initial=None):
    if initial is None:
        quotas = initial_quotas(users)
    else:
        quotas = copy.deepcopy(initial)

    ACTUALLY_ACCEPTED = ProjectMembership.ACTUALLY_ACCEPTED
    objs = ProjectMembership.objects.select_related('project', 'person')
    memberships = objs.filter(person__in=users,
                              state__in=ACTUALLY_ACCEPTED,
                              project__state=Project.APPROVED)

    project_ids = set(m.project_id for m in memberships)
    objs = ProjectApplication.objects.select_related('project')
    apps = objs.filter(project__in=project_ids)

    project_dict = {}
    for app in apps:
        project_dict[app.project] = app

    objs = ProjectResourceGrant.objects.select_related()
    grants = objs.filter(project_application__in=apps)

    for membership in memberships:
        uuid = membership.person.uuid
        userquotas = quotas.get(uuid, {})

        application = project_dict[membership.project]

        for grant in grants:
            if grant.project_application_id != application.id:
                continue

            source = get_grant_source(grant)
            source_quotas = userquotas.get(source, {})

            resource = grant.resource.full_name()
            prev = source_quotas.get(resource, 0)
            new = prev + grant.member_capacity
            source_quotas[resource] = new
            userquotas[source] = source_quotas
        quotas[uuid] = userquotas

    return quotas


def user_quotas(user):
    quotas = users_quotas([user])
    try:
        return quotas[user.uuid]
    except KeyError:
        raise ValueError("could not compute quotas")


def sync_users(users, sync=True):
    def _sync_users(users, sync):

        info = {}
        for user in users:
            info[user.uuid] = user.email

        qh_quotas, qh_limits = get_users_quotas_and_limits(users)
        astakos_initial = initial_quotas(users)
        astakos_quotas = users_quotas(users)

        diff_quotas = {}
        for holder, local in astakos_quotas.iteritems():
            registered = qh_limits.get(holder, None)
            if local != registered:
                diff_quotas[holder] = dict(local)

        if sync:
            r = set_user_quota(diff_quotas)

        return (qh_limits, qh_quotas,
                astakos_initial, diff_quotas, info)

    return _sync_users(users, sync)


def sync_all_users(sync=True):
    users = AstakosUser.objects.verified()
    return sync_users(users, sync)


def qh_add_resource_limit(resource, diff):
    users = AstakosUser.forupdate.all().select_for_update()
    qh.add_resource_limit(SYSTEM, resource, diff)


def qh_sync_new_resource(resource, limit):
    users = AstakosUser.forupdate.filter(
        email_verified=True).select_for_update()

    data = []
    for user in users:
        uuid = user.uuid
        key = uuid, SYSTEM, resource
        data.append((key, limit))

    qh.set_quota(data)

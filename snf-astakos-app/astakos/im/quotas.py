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

import copy
from astakos.im.models import (
    Resource, AstakosUserQuota, AstakosUser,
    Project, ProjectMembership, ProjectResourceGrant, ProjectApplication)
import astakos.quotaholder_app.callpoint as qh
from astakos.quotaholder_app.exception import NoCapacityError
from django.db.models import Q


def from_holding(holding):
    limit, usage_min, usage_max = holding
    body = {'limit':       limit,
            'usage':       usage_max,
            'pending':     usage_max-usage_min,
            }
    return body


def limits_only(holding):
    limit, usage_min, usage_max = holding
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


def get_counters(users, resources=None, sources=None):
    uuids = [user.uuid for user in users]

    counters = qh.get_quota(holders=uuids,
                            resources=resources,
                            sources=sources)
    return counters


def get_users_quotas(users, resources=None, sources=None):
    counters = get_counters(users, resources, sources)
    quotas = transform_data(counters)
    return quotas


def get_users_quota_limits(users, resources=None, sources=None):
    counters = get_counters(users, resources, sources)
    limits = transform_data(counters, limits_only)
    return limits


def get_user_quotas(user, resources=None, sources=None):
    quotas = get_users_quotas([user], resources, sources)
    return quotas.get(user.uuid, {})


def service_get_quotas(service, users=None):
    resources = Resource.objects.filter(service=service)
    resource_names = [r.name for r in resources]
    counters = qh.get_quota(holders=users, resources=resource_names)
    return transform_data(counters)


def _level_quota_dict(quotas):
    lst = []
    for holder, holder_quota in quotas.iteritems():
        for source, source_quota in holder_quota.iteritems():
            for resource, limit in source_quota.iteritems():
                key = (holder, source, resource)
                lst.append((key, limit))
    return lst


def _set_user_quota(quotas):
    q = _level_quota_dict(quotas)
    qh.set_quota(q)


def get_default_quota():
    _DEFAULT_QUOTA = {}
    resources = Resource.objects.select_related('service').all()
    for resource in resources:
        capacity = resource.uplimit
        _DEFAULT_QUOTA[resource.full_name()] = capacity

    return _DEFAULT_QUOTA


SYSTEM = 'system'
PENDING_APP_RESOURCE = 'astakos.pending_app'


def register_pending_apps(user, quantity, force=False):
    provision = (user.uuid, SYSTEM, PENDING_APP_RESOURCE), quantity
    try:
        s = qh.issue_commission(clientkey='astakos',
                                force=force,
                                provisions=[provision])
    except NoCapacityError as e:
        limit = e.data['limit']
        return False, limit
    qh.resolve_pending_commission('astakos', s)
    return True, None


def get_pending_app_quota(user):
    quota = get_user_quotas(user)
    return quota[SYSTEM][PENDING_APP_RESOURCE]


def add_base_quota(user, resource, capacity):
    resource = Resource.objects.get(name=resource)
    user = get_user_for_update(user.id)
    obj, created = AstakosUserQuota.objects.get_or_create(
        user=user, resource=resource, defaults={
            'capacity': capacity,
        })

    if not created:
        obj.capacity = capacity
        obj.save()
    qh_sync_locked_user(user)


def remove_base_quota(user, resource):
    user = get_user_for_update(user.id)
    AstakosUserQuota.objects.filter(
        user=user, resource__name=resource).delete()
    qh_sync_locked_user(user)


def initial_quotas(users):
    users = list(users)
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
        source_quota = user_init.get(SYSTEM, {})
        resource = user_quota.resource.full_name()
        source_quota[resource] = user_quota.capacity
        user_init[SYSTEM] = source_quota
        initial[uuid] = user_init

    return initial


def get_grant_source(grant):
    return SYSTEM


def astakos_users_quotas(users, initial=None):
    users = list(users)
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


def list_user_quotas(users):
    qh_quotas = get_users_quotas(users)
    astakos_initial = initial_quotas(users)
    return qh_quotas, astakos_initial


# Syncing to quotaholder

def get_users_for_update(user_ids):
    uids = sorted(user_ids)
    objs = AstakosUser.forupdate
    return list(objs.filter(id__in=uids).order_by('id').select_for_update())


def get_user_for_update(user_id):
    return get_users_for_update([user_id])[0]


def qh_sync_locked_users(users):
    astakos_quotas = astakos_users_quotas(users)
    _set_user_quota(astakos_quotas)


def qh_sync_users(users):
    uids = [user.id for user in users]
    users = get_users_for_update(uids)
    qh_sync_locked_users(users)


def qh_sync_users_diffs(users, sync=True):
    uids = [user.id for user in users]
    if sync:
        users = get_users_for_update(uids)

    astakos_quotas = astakos_users_quotas(users)
    qh_limits = get_users_quota_limits(users)
    diff_quotas = {}
    for holder, local in astakos_quotas.iteritems():
        registered = qh_limits.get(holder, None)
        if local != registered:
            diff_quotas[holder] = dict(local)

    if sync:
        _set_user_quota(diff_quotas)
    return qh_limits, diff_quotas


def qh_sync_locked_user(user):
    qh_sync_locked_users([user])


def qh_sync_user(user):
    qh_sync_users([user])


def members_to_sync(project):
    objs = ProjectMembership.objects.select_related('person')
    memberships = objs.filter(project=project,
                              state__in=ProjectMembership.ACTUALLY_ACCEPTED)
    return set(m.person for m in memberships)


def qh_sync_project(project):
    users = members_to_sync(project)
    qh_sync_users(users)


def qh_add_resource_limit(resource, diff):
    objs = AstakosUser.forupdate.filter(Q(email_verified=True) &
                                        ~Q(policy=resource))
    users = objs.order_by('id').select_for_update()
    uuids = [u.uuid for u in users]
    qh.add_resource_limit(holders=uuids, sources=[SYSTEM],
                          resources=[resource.name], diff=diff)


def qh_sync_new_resource(resource, limit):
    users = AstakosUser.forupdate.filter(
        email_verified=True).order_by('id').select_for_update()

    resource_name = resource.name
    data = []
    for user in users:
        uuid = user.uuid
        key = uuid, SYSTEM, resource_name
        data.append((key, limit))

    qh.set_quota(data)

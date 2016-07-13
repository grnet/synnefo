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

from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import Group

from synnefo.db.models import VirtualMachine
from astakos.im.models import AstakosUser, Project

from astakos.im.quotas import get_user_quotas

from synnefo.util import units

from synnefo_admin import admin_settings
from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.utils import (get_resource, is_resource_useful,
                                       create_details_href)


def get_groups():
    groups = Group.objects.all().values('name')
    return [(group['name'], '') for group in groups]


def get_user_or_404(query, for_update=False):
    """Get AstakosUser from query.

    The query can either be a user email, UUID or ID.
    """
    usr_obj = AstakosUser.objects.select_for_update() if for_update\
        else AstakosUser.objects

    if isinstance(query, basestring):
        q = Q(id=int(query)) if query.isdigit() else Q(uuid=query) | Q(email=query)
    elif isinstance(query, int) or isinstance(query, long):
        q = Q(id=int(query))
    else:
        raise TypeError("Unexpected type of query")

    try:
        return usr_obj.get(q)
    except ObjectDoesNotExist:
        raise AdminHttp404(
            "No User was found that matches this query: %s\n" % query)


def get_quotas(user):
    """Transform the resource usage dictionary of a user.

    Return a list of dictionaries that represent the quotas of the user. Each
    dictionary has the following form:

    {
        'project': <Project instance>,
        'resources': [('Resource Name1', <Resource dict>),
                      ('Resource Name2', <Resource dict>),...]
    }

    where 'Resource Name' is the name of the resource and <Resource dict> is
    the dictionary that is returned by list_user_quotas and has the following
    fields:

        pending, project_pending, project_limit, project_usage, usage.

    Note, the get_quota_usage function returns many dicts, but we only keep the
    ones that have limit > 0
    """
    usage = get_user_quotas(user)

    quotas = []
    for project_id, resource_dict in usage.iteritems():
        source = {}
        source['project'] = Project.objects.get(uuid=project_id)
        q_res = source['resources'] = []

        for resource_name, resource in resource_dict.iteritems():
            # Chech if the resource is useful to display
            project_limit = resource['project_limit']
            usage = resource['usage']
            r = get_resource(resource_name)
            if not is_resource_useful(r, project_limit, usage):
                continue

            usage = units.show(usage, r.unit)
            limit = units.show(resource['limit'], r.unit)
            taken_by_others = resource['project_usage'] - resource['usage']
            effective_limit = min(resource['limit'], project_limit - taken_by_others)
            if effective_limit < 0:
                effective_limit = 0
            effective_limit = units.show(effective_limit, r.unit)

            if limit != effective_limit:
                limit += " (Effective Limit: " + effective_limit + ")"

            q_res.append((r.report_desc, usage, limit,))

        quotas.append(source)

    return quotas


def get_enabled_providers(user):
    """Get a comma-seperated string with the user's enabled providers."""
    ep = [prov.module for prov in user.get_enabled_auth_providers()]
    return ", ".join(ep)


def get_user_groups(user):
    groups = ', '.join([g.name for g in user.groups.all()])
    if groups == '':
        return 'None'
    return groups


def get_suspended_vms(user):
    limit = admin_settings.ADMIN_LIMIT_SUSPENDED_VMS_IN_SUMMARY
    vms = VirtualMachine.objects.filter(userid=user.uuid, suspended=True).\
        order_by('-id')
    count = vms.count()
    if count == 0:
        return 'None'

    urls = [create_details_href('vm', vm.name, vm.pk) for vm in vms[:limit]]
    if count > limit:
        urls.append('...')
    return ', '.join(urls)

# Copyright (C) 2010-2014 GRNET S.A.
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

import logging
import re
from collections import OrderedDict

from operator import or_

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.template import Context, Template
from django.core.urlresolvers import set_urlconf

from synnefo.db.models import (VirtualMachine, Network, IPAddressLog, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import AstakosUser, ProjectMembership, Project, Resource
from astakos.im import user_logic as users

from astakos.im.quotas import get_user_quotas
from astakos.im.user_utils import send_plain as send_email

from synnefo.util import units

from eztables.views import DatatablesView

import django_filters
from django.db.models import Q

from synnefo_admin import admin_settings
from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.utils import (get_resource, is_resource_useful,
                                       create_details_href)

UUID_SEARCH_REGEX = re.compile('([0-9a-z]{8}-([0-9a-z]{4}-){3}[0-9a-z]{12})')


class DefaultUrlConf(object):

    """Context manager for setting and restoring the ROOT_URLCONF setting."""

    def __enter__(self):
        """Use the default ROOT_URLCONF."""
        set_urlconf("synnefo.webproject.urls")

    def __exit__(self, exc_type, exc_value, traceback):
        """Restore ROOT_URLCONF."""
        set_urlconf(None)


def get_groups():
    groups = Group.objects.all().values('name')
    return [(group['name'], '') for group in groups]


def get_user_or_404(query):
    """Get AstakosUser from query.

    The query can either be a user email, UUID or ID.
    """
    # Get by UUID
    try:
        return AstakosUser.objects.get(uuid=query)
    except ObjectDoesNotExist:
        pass

    # Get by Email
    try:
        return AstakosUser.objects.get(email=query)
    except ObjectDoesNotExist:
        pass

    # Get by ID
    try:
        return AstakosUser.objects.get(id=int(query))
    except (ObjectDoesNotExist, ValueError):
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
            r = get_resource(resource_name)
            if not is_resource_useful(r, project_limit):
                continue

            usage = units.show(resource['usage'], r.unit)
            limit = units.show(resource['limit'], r.unit)
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
    vms = VirtualMachine.objects.filter(userid=user.uuid, suspended=True)
    count = vms.count()
    if count == 0:
        return 'None'

    urls = [create_details_href('vm', vm.name, vm.pk) for vm in vms[:limit]]
    if count > limit:
        urls.append('...')
    return ', '.join(urls)

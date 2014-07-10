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

from synnefo.db.models import (VirtualMachine, Network, IPAddressLog, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import AstakosUser, ProjectMembership, Project, Resource
from astakos.im import user_logic as users

from astakos.im.quotas import list_user_quotas
from astakos.im.user_utils import send_plain as send_email

from synnefo.util import units

from eztables.views import DatatablesView

import django_filters
from django.db.models import Q

from synnefo_admin.admin.utils import is_resource_useful, create_details_href

UUID_SEARCH_REGEX = re.compile('([0-9a-z]{8}-([0-9a-z]{4}-){3}[0-9a-z]{12})')


def get_groups():
    groups = Group.objects.all().values('name')
    return [(group['name'], '') for group in groups]


def get_user(query):
    """Get AstakosUser from query.

    The query can either be a user email or a UUID.
    """
    is_uuid = UUID_SEARCH_REGEX.match(query)

    try:
        if is_uuid:
            user = AstakosUser.objects.get(uuid=query)
        else:
            user = AstakosUser.objects.get(email=query)
    except ObjectDoesNotExist:
        logging.error("Failed to resolve '%s' into account" % query)
        return None

    return user


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
    ones that have project_limit > 0
    """
    usage = list_user_quotas([user])[user.uuid]

    quotas = []
    for project_id, resource_dict in usage.iteritems():
        source = {}
        source['project'] = Project.objects.get(uuid=project_id)
        q_res = source['resources'] = []

        for resource_name, resource in resource_dict.iteritems():
            # Chech if the resource is useful to display
            r = Resource.objects.get(name=resource_name)
            limit = resource['project_limit']
            if not is_resource_useful(r, limit):
                continue

            for p, value in resource.iteritems():
                resource[p] = units.show(value, r.unit)
            q_res.append((r.report_desc, resource))

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
    vms = VirtualMachine.objects.filter(userid=user.uuid, suspended=True)
    if not vms:
        return 'None'

    urls = [create_details_href('vm', vm.name, vm.pk) for vm in vms]
    return ', '.join(urls)

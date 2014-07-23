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
from operator import itemgetter

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import (VirtualMachine, Network, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import (AstakosUser, Project, ProjectResourceGrant,
                               Resource)

from eztables.views import DatatablesView
from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from astakos.im.user_utils import send_plain as send_email
from astakos.im.functions import (validate_project_action, ProjectConflict,
                                  approve_application, deny_application,
                                  suspend, unsuspend, terminate, reinstate)
from astakos.im.quotas import get_project_quota

from synnefo.util import units

import django_filters
from django.db.models import Q

from synnefo_admin.admin.exceptions import AdminHttp404
from synnefo_admin.admin.utils import get_resource, is_resource_useful

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)


def get_actual_owner(inst):
    if inst.owner:
        return inst.owner
    try:
        return inst.members.all()[0]
    except IndexError:
        return None


def get_project_or_404(query):
    # Get by UUID
    try:
        return Project.objects.get(uuid=query)
    except ObjectDoesNotExist:
        pass

    # Get by ID
    try:
        return Project.objects.get(id=query)
    except (ObjectDoesNotExist, ValueError):
        raise AdminHttp404(
            "No Project was found that matches this query: %s\n" % query)


def get_contact_email(inst):
    owner = get_actual_owner(inst)
    if owner:
        return owner.email


def get_contact_name(inst):
    owner = get_actual_owner(inst)
    if owner:
        return owner.realname


def get_contact_id(inst):
    owner = get_actual_owner(inst)
    if owner:
        return owner.uuid


def get_policies(inst):
    policies = inst.projectresourcequota_set.all().prefetch_related('resource')
    policy_list = []

    for p in policies:
        r = p.resource
        if not is_resource_useful(r, p.project_capacity):
            continue
        policy_list.append(p)

    return policy_list


def get_project_usage(inst):
    """Return requested project quota type.

    Accepted stats are: 'project_limit', 'project_pending', 'project_usage'.
    Note that the output is sanitized, meaning that stats that correspond
    to infinite or zero limits will not be returned.
    """
    resource_list = []
    quota_dict = get_project_quota(inst)
    if not quota_dict:
        return []

    policies = get_policies(inst)
    for p in policies:
        r = p.resource
        value = units.show(quota_dict[r.name]['project_usage'], r.unit)
        resource_list.append((r.report_desc, value))

    return resource_list


def get_project_quota_category(inst, category):
    """Get the quota for project member"""
    resource_list = []
    policies = get_policies(inst)

    for p in policies:
        r = p.resource
        # Get human-readable (resource name, member capacity) tuple
        if category == "member":
            resource_list.append((r.report_desc, p.display_member_capacity()))
        elif category == "limit":
            resource_list.append((r.report_desc, p.display_project_capacity()))

    return resource_list


def display_quota_horizontally(resource_list):
    """Display resource lists in one line."""
    if not resource_list:
        return "-"
    return ', '.join((': '.join(pair) for pair in resource_list))


def display_project_usage_horizontally(inst):
    """Display the requested project stats in a one-line string."""
    resource_list = get_project_usage(inst)
    return display_quota_horizontally(resource_list)


def display_member_quota_horizontally(inst):
    """Display project resources (member or total) in one line."""
    resource_list = get_project_quota_category(inst, "member")
    return display_quota_horizontally(resource_list)


def display_project_limit_horizontally(inst):
    """Display project resources (member or total) in one line."""
    resource_list = get_project_quota_category(inst, "limit")
    return display_quota_horizontally(resource_list)

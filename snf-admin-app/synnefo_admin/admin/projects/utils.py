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

from synnefo_admin.admin.utils import is_resource_useful

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)


def get_project(query):
    try:
        project = Project.objects.get(id=query)
    except Exception:
        project = Project.objects.get(uuid=query)
    return project


def get_contact_mail(inst):
    if inst.owner:
        return inst.owner.email,


def get_contact_name(inst):
    if inst.owner:
        return inst.owner.realname,


def get_contact_id(inst):
    if inst.owner:
        return inst.owner.uuid


def display_project_stats(inst, stat):
    """Display the requested project stats in a one-line string.

    Accepted stats are: 'project_limit', 'project_pending', 'project_usage'.
    Note that the output is sanitized, meaning that stats that correspond
    to infinite or zero limits will not be shown.
    """
    resource_list = []
    quota_dict = get_project_quota(inst)

    for resource_name, stats in quota_dict.iteritems():
        resource = Resource.objects.get(name=resource_name)
        if not is_resource_useful(resource, stats['project_limit']):
            continue
        value = units.show(stats[stat], resource.unit)
        resource_list.append((resource.display_name, value))

    resource_list = sorted(resource_list, key=itemgetter(0))
    if not resource_list:
        return "-"
    return ', '.join((': '.join(pair) for pair in resource_list))


def display_project_resources(inst, type):
    """Display project resources (member of total) in one line."""
    resource_list = []
    prqs = inst.resource_set

    for prq in prqs:
        r = prq.resource

        # Check the project limit to verify that we can print this resource
        if not is_resource_useful(r, prq.project_capacity):
            continue

        # Get human-readable (resource name, member capacity) tuple
        if type == 'member':
            resource_list.append((r.display_name,
                                  prq.display_member_capacity()))
        # Get human-readable (resource name, total capacity) tuple
        elif type == 'total':
            resource_list.append((r.display_name,
                                  prq.display_project_capacity()))
        else:
            raise Exception("Wrong type")

    resource_list = sorted(resource_list, key=itemgetter(0))
    return ', '.join((': '.join(pair) for pair in resource_list))

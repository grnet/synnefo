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


class ProjectAction(AdminAction):

    """Class for actions on projects. Derived from AdminAction.

    Pre-determined Attributes:
    target:        project
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='project', f=f, **kwargs)


def check_project_action(action):
    return lambda p: validate_project_action(p, action)


def check_approve(project):
    if project.is_base:
        return False
    return project.last_application.can_approve()


def check_deny(project):
    if project.is_base:
        return False
    return project.last_application.can_deny()


def generate_actions():
    """Create a list of actions on projects.

    The actions are: approve/deny, suspend/unsuspend, terminate/reinstate,
    contact
    """
    actions = OrderedDict()

    actions['approve'] = ProjectAction(name='Approve', f=approve_application,
                                       c=check_approve,
                                       karma='good',
                                       allowed_groups=['superadmin'])

    actions['deny'] = ProjectAction(name='Deny', f=deny_application,
                                    c=check_deny, karma='bad',
                                    caution_level='warning',
                                    allowed_groups=['superadmin'])

    actions['suspend'] = ProjectAction(name='Suspend', f=suspend,
                                       c=check_project_action("SUSPEND"),
                                       karma='bad', caution_level='warning',
                                       allowed_groups=['superadmin'])

    actions['unsuspend'] = ProjectAction(name='Release suspension',
                                         f=unsuspend,
                                         c=check_project_action("UNSUSPEND"),
                                         karma='good', caution_level='warning',
                                         allowed_groups=['superadmin'])

    actions['terminate'] = ProjectAction(name='Terminate', f=terminate,
                                         c=check_project_action("TERMINATE"),
                                         karma='bad',
                                         caution_level='dangerous',
                                         allowed_groups=['superadmin'])

    actions['reinstate'] = ProjectAction(name='Reinstate', f=reinstate,
                                         c=check_project_action("REINSTATE"),
                                         karma='good', caution_level='warning',
                                         allowed_groups=['superadmin'])

    actions['contact'] = ProjectAction(name='Send e-mail', f=send_email,
                                       allowed_groups=['admin', 'superadmin'])

    return actions


def get_permitted_actions(user):
    actions = generate_actions()
    for key, action in actions.iteritems():
        if not action.is_user_allowed(user):
            actions.pop(key, None)
    return actions


def get_allowed_actions(project):
    """Get a list of actions that can apply to a project."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        try:
            if action.can_apply(project):
                allowed_actions.append(key)
        except ProjectConflict:
            pass

    return allowed_actions

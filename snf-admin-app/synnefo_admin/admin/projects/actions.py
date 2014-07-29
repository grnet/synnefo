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
                                         has_permission_or_403,
                                         AdminActionCannotApply)
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
from synnefo_admin.admin.utils import update_actions_rbac, send_admin_email


class ProjectAction(AdminAction):

    """Class for actions on projects. Derived from AdminAction.

    Pre-determined Attributes:
    target:        project
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='project', f=f, **kwargs)


# FIXME: This check should be done by astakos
def custom_check_suspend(project):
    if project.is_suspended:
        return False
    else:
        res, _ = validate_project_action(project, "SUSPEND")
        return res


def do_project_action(action):

    if action == 'approve':
        return lambda p: approve_application(p.last_application.id)
    elif action == 'deny':
        return lambda p: deny_application(p.last_application.id)
    else:
        # The action name is the same as the imported action. If the imported
        # action name changes, then this code must change too.
        return lambda p: globals()[action](p.id)


def check_project_action(action):
    def check(p, action):
        res, _ = validate_project_action(p, action)
        return res

    return lambda p: check(p, action)


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

    actions['approve'] = ProjectAction(name='Approve',
                                       f=do_project_action("approve"),
                                       c=check_approve, karma='good',)

    actions['deny'] = ProjectAction(name='Deny',
                                    f=do_project_action("deny"), c=check_deny,
                                    karma='bad', caution_level='warning',)

    actions['suspend'] = ProjectAction(name='Suspend',
                                       f=do_project_action("suspend"),
                                       c=custom_check_suspend,
                                       karma='bad', caution_level='warning',)

    actions['unsuspend'] = ProjectAction(name='Unsuspend',
                                         f=do_project_action("unsuspend"),
                                         c=check_project_action("UNSUSPEND"),
                                         karma='good', caution_level='warning',)

    actions['terminate'] = ProjectAction(name='Terminate',
                                         f=do_project_action("terminate"),
                                         c=check_project_action("TERMINATE"),
                                         karma='bad',
                                         caution_level='dangerous',)

    actions['reinstate'] = ProjectAction(name='Reinstate',
                                         f=do_project_action("reinstate"),
                                         c=check_project_action("REINSTATE"),
                                         karma='good',
                                         caution_level='warning',)

    actions['contact'] = ProjectAction(name='Send e-mail', f=send_admin_email,)

    update_actions_rbac(actions)

    return actions
cached_actions = generate_actions()

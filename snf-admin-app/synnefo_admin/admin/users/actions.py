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

from astakos.api.quotas import get_quota_usage
from astakos.im.user_utils import send_plain as send_email

from synnefo.util import units

from eztables.views import DatatablesView

import django_filters
from django.db.models import Q

from synnefo_admin.admin.actions import AdminAction, noop

class UserAction(AdminAction):

    """Class for actions on users. Derived from AdminAction.

    Pre-determined Attributes:
        target:        user
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='user', f=f, **kwargs)


def check_user_action(action):
    return lambda u: users.validate_user_action(u, action)


def generate_actions():
    """Create a list of actions on users.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['activate'] = UserAction(name='Activate', f=users.activate,
                                     c=check_user_action("ACTIVATE"),
                                     karma='good',
                                     allowed_groups=['superadmin'])

    actions['deactivate'] = UserAction(name='Deactivate', f=users.deactivate,
                                       c=check_user_action("DEACTIVATE"),
                                       karma='bad', caution_level='warning',
                                       allowed_groups=['superadmin'])

    actions['accept'] = UserAction(name='Accept', f=users.accept,
                                   c=check_user_action("ACCEPT"),
                                   karma='good',
                                   allowed_groups=['superadmin'])

    actions['reject'] = UserAction(name='Reject', f=users.reject,
                                   c=check_user_action("REJECT"),
                                   karma='bad', caution_level='dangerous',
                                   allowed_groups=['superadmin'])

    actions['verify'] = UserAction(name='Verify', f=users.verify,
                                   c=check_user_action("VERIFY"),
                                   karma='good',
                                   allowed_groups=['superadmin'])

    actions['resend_verification'] = UserAction(
        name='Resend verification', f=users.send_verification_mail,
        karma='good', c=check_user_action("SEND_VERIFICATION_MAIL"),
        allowed_groups=['admin', 'superadmin'])

    actions['contact'] = UserAction(name='Send e-mail', f=send_email,
                                    allowed_groups=['admin', 'superadmin'])
    return actions


def get_permitted_actions(user):
    actions = generate_actions()
    for key, action in actions.iteritems():
        if not action.is_user_allowed(user):
            actions.pop(key, None)
    return actions


def get_allowed_actions(user):
    """Get a list of actions that can apply to a user."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(user):
            allowed_actions.append(key)

    return allowed_actions

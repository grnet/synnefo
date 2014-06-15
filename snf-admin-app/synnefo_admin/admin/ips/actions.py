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

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import IPAddress
from synnefo.logic import ips
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import filter_owner_name


class IPAction(AdminAction):

    """Class for actions on ips. Derived from AdminAction.

    Pre-determined Attributes:
        target:        ip
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='ip', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on ips.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['delete'] = IPAction(name='Delete', f=ips.delete_floating_ip,
                                 karma='bad', reversible=False,
                                 allowed_groups=['superadmin'])

    actions['reassign'] = IPAction(name='Reassign to project', f=noop,
                                   karma='neutral', reversible=True,
                                   allowed_groups=['superadmin'])

    actions['contact'] = IPAction(name='Send e-mail', f=send_email,
                                  allowed_groups=['admin', 'superadmin'])
    return actions


def get_permitted_actions(user):
    actions = generate_actions()
    for key, action in actions.iteritems():
        if not action.is_user_allowed(user):
            actions.pop(key, None)
    return actions


def get_allowed_actions(ip):
    """Get a list of actions that can apply to a ip."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(ip):
            allowed_actions.append(key)

    return allowed_actions

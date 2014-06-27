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
from collections import OrderedDict

from django.core.urlresolvers import reverse

from synnefo.db.models import Volume
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView

import django_filters

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import update_actions_rbac
from synnefo_admin.admin.utils import filter_owner_name


class VolumeAction(AdminAction):

    """Class for actions on volumes. Derived from AdminAction.

    Pre-determined Attributes:
        target:        volume
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='volume', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on volumes.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['contact'] = VolumeAction(name='Send e-mail', f=send_email,)

    update_actions_rbac(actions)

    return actions
cached_actions = generate_actions()

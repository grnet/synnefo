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

from synnefo.logic import ips

from synnefo_admin.admin.actions import AdminAction, noop
from synnefo_admin.admin.utils import update_actions_rbac, send_admin_email


class IPAction(AdminAction):

    """Class for actions on ips. Derived from AdminAction.

    Pre-determined Attributes:
        target:        ip
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='ip', f=f, **kwargs)


def check_ip_action(action):
    """Check if an action can apply to an IP.

    This is a wrapper for `validate_ip_action` of the ips module, that handles
    the tupples returned by it.
    """
    def check(ip, action):
        res, _ = ips.validate_ip_action(ip, action)
        return res

    return lambda ip: check(ip, action)


def generate_actions():
    """Create a list of actions on ips."""
    actions = OrderedDict()

    actions['destroy'] = IPAction(name='Destroy', c=check_ip_action("DELETE"),
                                  f=ips.delete_floating_ip, karma='bad',
                                  caution_level='dangerous',)

    actions['reassign'] = IPAction(name='Reassign to project', f=noop,
                                   karma='neutral', caution_level='dangerous',)

    actions['contact'] = IPAction(name='Send e-mail', f=send_admin_email,)

    update_actions_rbac(actions)

    return actions
cached_actions = generate_actions()

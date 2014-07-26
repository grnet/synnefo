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

from synnefo.db.models import (Network, VirtualMachine, NetworkInterface,
                               IPAddress)
from synnefo.logic.networks import validate_network_action
from synnefo.logic import networks
from astakos.im.models import AstakosUser, Project

from eztables.views import DatatablesView
import django_filters

from synnefo_admin.admin.actions import (AdminAction, noop,
                                         has_permission_or_403)
from synnefo_admin.admin.utils import update_actions_rbac, send_admin_email


class NetworkAction(AdminAction):

    """Class for actions on networks. Derived from AdminAction.

    Pre-determined Attributes:
        target:        network
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='network', f=f, **kwargs)


def drain_network(network):
    network.drained = True
    network.save()


def undrain_network(network):
    network.drained = False
    network.save()


def check_network_action(action):
    if action == "contact":
        # Contact action is allowed only on private networks. However, this
        # function may get called with an AstakosUser as a target. In this
        # case, we always confirm the action.
        return lambda n: not getattr(n, 'public', False)
    else:
        return lambda n: validate_network_action(n, action)


def generate_actions():
    """Create a list of actions on networks.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = OrderedDict()

    actions['drain'] = NetworkAction(name='Drain', f=drain_network,
                                     #c=check_network_action('DRAIN'),
                                     caution_level=True,)

    actions['undrain'] = NetworkAction(name='Undrain', f=undrain_network,
                                       #c=check_network_action('UNDRAIN'),
                                       karma='neutral',)

    actions['destroy'] = NetworkAction(name='Destroy', f=networks.delete,
                                       c=check_network_action('DESTROY'),
                                       karma='bad', caution_level='dangerous',)

    actions['reassign'] = NetworkAction(name='Reassign to project', f=noop,
                                        karma='neutral',
                                        caution_level='dangerous',)

    actions['change_owner'] = NetworkAction(name='Change owner', f=noop,
                                            karma='neutral',
                                            caution_level='dangerous',)

    actions['contact'] = NetworkAction(name='Send e-mail', f=send_admin_email,
                                       c=check_network_action("contact"),)

    update_actions_rbac(actions)

    return actions
cached_actions = generate_actions()

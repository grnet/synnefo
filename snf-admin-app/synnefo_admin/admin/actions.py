# Copyright 2012 - 2014 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import functools

from snf_django.lib.api import faults
from astakos.im.functions import ProjectConflict


class AdminAction:

    """Generic class for actions on admin targets.

    Attributes:
        name:           The name of the action
        target:         The target group of the action
        check:          The function that will trigger once an action is
                        requested.
        allowed_groups: The groups that are allowed to author this action.
        karma:          The impact of the action.
                        Accepted values: good, neutral, bad.
        caution_level:  Indication of how much careful the user should be:
                        Accepted values: none, warning, dangerous.
        description:    A short text that describes an action

    Methods:
        f:              The function that will trigger once an action is
                        requested.
        can_apply:      The function that checks if an action can be applied to
                        a user.
    """

    def __init__(self, name, target, f, c=None, allowed_groups='admin',
                 karma='neutral', caution_level='none', description=''):
        """Initialize the AdminAction class."""
        self.name = name
        self.description = description
        self.target = target
        self.karma = karma
        self.caution_level = caution_level
        self.allowed_groups = allowed_groups
        self.f = f
        if c:
            self.check = c

    def can_apply(self, t):
        """Check if an action can apply to a target.

        If no check function has been registered for this action, this method
        will answer always "True".
        """
        # Check if a check function has been registered
        if not hasattr(self, 'check'):
            return True

        try:
            res = self.check(t)
        # Cyclades raises BadRequest when an action is not supported for an
        # instance.
        except faults.BadRequest:
            return False
        # Astakos raises ProjectConflict when an action is not supported for an
        # instance.
        except ProjectConflict:
            return False

        # We accept "None" as correct value.
        if res is None:
            res = True
        return res

    def is_user_allowed(self, user):
        """Check if a user can author an action."""
        groups = get_user_groups(user)
        return set(groups) & set(self.allowed_groups)


class AdminActionNotPermitted(Exception):

    """Exception when an action is not permitted."""

    pass


class AdminActionUnknown(Exception):

    """Exception when an action is unknown."""

    pass


class AdminActionNotImplemented(Exception):

    """Exception when an action is not implemented."""

    pass


def noop(*args, **kwargs):
    """Placeholder function."""
    raise AdminActionNotImplemented


def get_user_groups(user):
    """Extract user groups from request.

    This function requires that astakos client has already stored the user data
    in the request.
    """
    if not user:
        return None
    elif isinstance(user, dict):
        groups = user['access']['user']['roles']
        return [g["name"] for g in groups]
    else:
        raise Exception


def has_permission_or_403(actions):
    """API decorator for user permissions for actions.

    Check if a user (retrieved from Astakos client) can author an action. If
    not, raise an AdminActionNotPermitted exception.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, op, *args, **kwargs):
            if not isinstance(actions, dict):
                raise AdminActionNotImplemented
            if not actions[op].is_user_allowed(request.user):
                raise AdminActionNotPermitted
            return func(request, op, *args, **kwargs)
        return wrapper
    return decorator


def get_permitted_actions(actions, user):
    """Get a list of actions that a user is permitted to author."""
    for key, action in actions.iteritems():
        if not action.is_user_allowed(user):
            actions.pop(key, None)
    return actions


def get_allowed_actions(actions, inst, user=None):
    """Get a list of actions that can apply to an instance.

    Optionally, if the `user` argument is passed, we return the intersection of
    the permitted actions for the user and the allowed actions for the
    instance.
    """
    allowed_actions = []
    if user:
        actions = get_permitted_actions(actions, user)

    for key, action in actions.iteritems():
        if action.can_apply(inst):
            allowed_actions.append(key)

    return allowed_actions

# Copyright (C) 2010-2017 GRNET S.A.
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


from astakos.im import activation_backends, functions
import astakos.im.messages as astakos_messages

from snf_django.lib.api import faults

activation_backend = activation_backends.get_backend()
validate_user_action = activation_backend.validate_user_action


##
# Actions: The necessary logic for actions on a user. Uses extensively
# the activation_backends.
def reject(user, reason, notify_user=True):
    """Reject a user."""
    res = activation_backend.handle_moderation(
        user, accept=False, reject_reason=reason)
    if notify_user:
        activation_backend.send_result_notifications(res, user)
    return res


def verify(user, verification_code, notify_user=False):
    """Verify a user's mail."""
    res = activation_backend.handle_verification(user, verification_code)
    if notify_user:
        activation_backend.send_result_notifications(res, user)
    return res


def accept(user, notify_user=True):
    """Accept a verified user."""
    res = activation_backend.handle_moderation(user, accept=True)
    if notify_user:
        activation_backend.send_result_notifications(res, user)
    return res


def activate(user):
    """Activate an inactive user."""
    res = activation_backend.activate_user(user)
    return res


def deactivate(user, reason=""):
    """Deactivate an active user."""
    res = activation_backend.deactivate_user(user, reason=reason)
    return res


def send_verification_mail(user):
    """Send verification mail to an unverified user."""
    res = activation_backend.send_user_verification_email(user)
    return res


def set_default_project(user, project_id):
    """Set default project for an active user."""
    if not user.email_verified:
        msg = astakos_messages.ACCOUNT_NOT_VERIFIED
        raise faults.NotAllowed(msg)
    if not user.moderated:
        msg = astakos_messages.ACCOUNT_NOT_MODERATED
        raise faults.NotAllowed(msg)
    if user.is_rejected:
        msg = astakos_messages.ACCOUNT_REJECTED
        raise faults.NotAllowed(msg)
    if not user.is_active:
        msg = astakos_messages.ACCOUNT_NOT_ACTIVE
        raise faults.NotAllowed(msg)

    try:
        project = functions.validate_project_member_state(user, project_id)
    except functions.ProjectNotFound as pnf:
        raise faults.ItemNotFound(pnf.message)
    except functions.ProjectForbidden as pf:
        raise faults.Forbidden(pf.message)

    user.default_project = project.uuid
    user.save()

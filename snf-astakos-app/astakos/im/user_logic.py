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


from astakos.im import activation_backends

activation_backend = activation_backends.get_backend()
validate_user_action = activation_backend.validate_user_action


##
# Actions: The necessary logic for actions on a user. Uses extensively
# the activation_backends.
def reject(user, reason):
    """Reject a user."""
    res = activation_backend.handle_moderation(
        user, accept=False, reject_reason=reason)
    activation_backend.send_result_notifications(res, user)
    return res


def verify(user, verification_code, notify_user=False):
    """Verify a user's mail."""
    res = activation_backend.handle_verification(user, verification_code)
    if notify_user:
        activation_backend.send_result_notifications(res, user)
    return res


def accept(user):
    """Accept a verified user."""
    res = activation_backend.handle_moderation(user, accept=True)
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

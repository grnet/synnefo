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

from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from snf_django.lib.api import faults

from astakos.im import models
from astakos.im import functions
from astakos.im import settings
from astakos.im import forms
from astakos.im import user_utils

import astakos.im.messages as astakos_messages

import datetime
import logging
import re
import json

logger = logging.getLogger(__name__)


def get_backend():
    """
    Returns an instance of an activation backend,
    according to the INVITATIONS_ENABLED setting
    (if True returns ``astakos.im.activation_backends.InvitationsBackend``
    and if False
    returns ``astakos.im.activation_backends.SimpleBackend``).

    If the backend cannot be located
    ``django.core.exceptions.ImproperlyConfigured`` is raised.
    """
    module = 'astakos.im.activation_backends'
    prefix = 'Invitations' if settings.INVITATIONS_ENABLED else 'Simple'
    backend_class_name = '%sBackend' % prefix
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured(
            'Error loading activation backend %s: "%s"' % (module, e))
    try:
        backend_class = getattr(mod, backend_class_name)
    except AttributeError:
        raise ImproperlyConfigured(
            'Module "%s" does not define a activation backend named "%s"' % (
                module, backend_class_name))
    return backend_class(settings.MODERATION_ENABLED)


class ActivationBackend(object):
    """
    ActivationBackend handles user verification/activation.

    Example usage::
    #>>> # it is wise to not instantiate a backend class directly but use
    #>>> # get_backend method instead.
    #>>> backend = get_backend()
    #>>> formCls = backend.get_signup_form(request.POST)
    #>>> if form.is_valid():
    #>>>     user = form.create_user()
    #>>>     activation = backend.handle_registration(user)
    #>>>     # activation.status is one of backend.Result.{*} activation result
    #>>>     # types
    #>>>
    #>>>     # sending activation notifications is not done automatically
    #>>>     # we need to call send_result_notifications
    #>>>     backend.send_result_notifications(activation)
    #>>>     return HttpResponse(activation.message)
    """

    verification_template_name = 'im/activation_email.txt'
    greeting_template_name = 'im/welcome_email.txt'
    pending_moderation_template_name = \
        'im/account_pending_moderation_notification.txt'
    activated_email_template_name = 'im/account_activated_notification.txt'

    class Result:
        # user created, email verification sent
        PENDING_VERIFICATION = 1
        # email verified
        PENDING_MODERATION = 2
        # user moderated
        ACCEPTED = 3
        # user rejected
        REJECTED = 4
        # inactive user activated
        ACTIVATED = 5
        # active user deactivated
        DEACTIVATED = 6
        # something went wrong
        ERROR = -1

    def __init__(self, moderation_enabled):
        self.moderation_enabled = moderation_enabled

    def _is_preaccepted(self, user):
        """
        Decide whether user should be automatically moderated. The method gets
        called only when self.moderation_enabled is set to True.

        The method returns False or a string identifier which later will be
        stored in user's accepted_policy field. This is helpfull for
        administrators to be aware of the reason a created user was
        automatically activated.
        """

        # check preaccepted mail patterns
        for pattern in settings.RE_USER_EMAIL_PATTERNS:
            if re.match(pattern, user.email):
                return 'email'

        # provider automoderate policy is on
        if user.get_auth_provider().get_automoderate_policy:
            return 'auth_provider_%s' % user.get_auth_provider().module

        return False

    def get_signup_form(self, provider='local', initial_data=None, **kwargs):
        """
        Returns a form instance for the type of registration the user chosen.
        This can be either a LocalUserCreationForm for classic method signups
        or ThirdPartyUserCreationForm for users who chosen to signup using a
        federated login method.
        """
        main = provider.capitalize() if provider == 'local' else 'ThirdParty'
        suffix = 'UserCreationForm'
        formclass = getattr(forms, '%s%s' % (main, suffix))
        kwargs['provider'] = provider
        return formclass(initial_data, **kwargs)

    def prepare_user(self, user, email_verified=None):
        """ Initialization of a newly registered user.

        The method sets email verification code. If email_verified is set to
        True or the provider's policy dictates that the email is automatically
        verified we automatically process user through the verification step.

        """
        logger.info("Initializing user registration %s", user.log_display)

        reason = None
        if not email_verified:
            if user.get_auth_provider().get_autoverify_policy:
                # Verify email according to provider's policy
                email_verified = True
                reason = "skip email verification provider's policy."

        user.renew_verification_code()
        user.save()

        if email_verified:
            msg = "Auto verifying user email %s." % user.log_display
            if reason:
                msg += " reason: %s" % reason
            logger.info(msg)
            return self.verify_user(user,
                                    user.verification_code)

        return ActivationResult(self.Result.PENDING_VERIFICATION)

    def validate_user_action(self, user, action, verification_code='',
                             silent=True):
        """Check if an action can apply on a user.

        Arguments:
            user: The target user.
            action: The name of the action (in capital letters).
            verification_code: Needed only in "VERIFY" action.
            silent: If set to True, suppress exceptions.

        Returns:
            A `(success, message)` tuple. `success` is a boolean value that
            shows if the action can apply on a user, and `message` explains
            why the action cannot apply on a user.

            If an action can apply on a user, this function will always return
            `(True, None)`.

        Exceptions:
            faults.NotAllowed: When the action cannot apply on a user.
            faults.BadRequest: When the action is unknown/malformed.
        """
        def fail(e=Exception, msg=""):
            if silent:
                return False, msg
            else:
                raise e(msg)

        if action == "VERIFY":
            if user.email_verified:
                msg = _(astakos_messages.ACCOUNT_ALREADY_VERIFIED)
                return fail(faults.NotAllowed, msg)
            if not (user.verification_code and
                    user.verification_code == verification_code):
                msg = _(astakos_messages.VERIFICATION_FAILED)
                return fail(faults.NotAllowed, msg)

        elif action == "ACCEPT":
            if user.moderated and not user.is_rejected:
                msg = _(astakos_messages.ACCOUNT_ALREADY_MODERATED)
                return fail(faults.NotAllowed, msg)
            if not user.email_verified:
                msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
                return fail(faults.NotAllowed, msg)

        elif action == "ACTIVATE":
            if not user.email_verified:
                msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
                return fail(faults.NotAllowed, msg)
            if not user.moderated:
                msg = _(astakos_messages.ACCOUNT_NOT_MODERATED)
                return fail(faults.NotAllowed, msg)
            if user.is_rejected:
                msg = _(astakos_messages.ACCOUNT_REJECTED)
                return fail(faults.NotAllowed, msg)
            if user.is_active:
                msg = _(astakos_messages.ACCOUNT_ALREADY_ACTIVE)
                return fail(faults.NotAllowed, msg)

        elif action == "DEACTIVATE":
            if not user.email_verified:
                msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
                return fail(faults.NotAllowed, msg)
            if not user.moderated:
                msg = _(astakos_messages.ACCOUNT_NOT_MODERATED)
                return fail(faults.NotAllowed, msg)
            if user.is_rejected:
                msg = _(astakos_messages.ACCOUNT_REJECTED)
                return fail(faults.NotAllowed, msg)

        elif action == "REJECT":
            if user.moderated:
                msg = _(astakos_messages.ACCOUNT_ALREADY_MODERATED)
                return fail(faults.NotAllowed, msg)
            if user.is_active:
                msg = _(astakos_messages.ACCOUNT_ALREADY_ACTIVE)
                return fail(faults.NotAllowed, msg)
            if not user.email_verified:
                msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
                return fail(faults.NotAllowed, msg)

        elif action == "SEND_VERIFICATION_MAIL":
            if user.email_verified:
                return fail(faults.NotAllowed)

        else:
            return fail(faults.BadRequest,
                        "Unknown action: {}.".format(action))

        return True, None

    def verify_user(self, user, verification_code):
        """
        Process user verification using provided verification_code. This
        should take place in user activation view. If no moderation is enabled
        we automatically process user through activation process.
        """
        logger.info("Verifying user: %s", user.log_display)

        ok, msg = self.validate_user_action(user, "VERIFY", verification_code)
        if not ok:
            if msg == _(astakos_messages.ACCOUNT_ALREADY_VERIFIED):
                logger.warning("User email already verified: %s",
                               user.log_display)
            elif msg == _(astakos_messages.VERIFICATION_FAILED):
                logger.error("User email verification failed (invalid "
                             "verification code): %s", user.log_display)
            return ActivationResult(self.Result.ERROR, msg)

        user.email_verified = True
        user.verified_at = datetime.datetime.now()
        # invalidate previous code
        user.renew_verification_code()
        user.save()
        logger.info("User email verified: %s", user.log_display)

        if not self.moderation_enabled:
            logger.warning("User preaccepted (%s): %s", 'auto_moderation',
                           user.log_display)
            return self.accept_user(user, policy='auto_moderation')

        preaccepted = self._is_preaccepted(user)
        if preaccepted:
            logger.warning("User preaccepted (%s): %s", preaccepted,
                           user.log_display)
            return self.accept_user(user, policy=preaccepted)

        if user.moderated:
            # set moderated to false because accept_user will return error
            # result otherwise.
            user.moderated = False
            return self.accept_user(user, policy='already_moderated')
        else:
            return ActivationResult(self.Result.PENDING_MODERATION)

    def accept_user(self, user, policy='manual'):
        logger.info("Moderating user: %s", user.log_display)

        ok, msg = self.validate_user_action(user, "ACCEPT")
        if not ok:
            if msg == _(astakos_messages.ACCOUNT_ALREADY_MODERATED):
                logger.warning("User already accepted, moderation skipped: %s",
                               user.log_display)
            elif msg == _(astakos_messages.ACCOUNT_NOT_VERIFIED):
                logger.warning("Cannot accept unverified user: %s",
                               user.log_display)
            return ActivationResult(self.Result.ERROR, msg)

        # store a snapshot of user details by the time he
        # got accepted.

        if not user.accepted_email:
            user.accepted_email = user.email
        user.accepted_policy = policy
        user.moderated = True
        user.moderated_at = datetime.datetime.now()
        user.moderated_data = json.dumps(user.__dict__,
                                         default=lambda obj:
                                         unicode(obj))
        user.save()
        functions.enable_base_project(user)

        if user.is_rejected:
            logger.warning("User has previously been "
                           "rejected, reseting rejection state: %s",
                           user.log_display)
            user.is_rejected = False
            user.rejected_at = None

        user.save()
        logger.info("User accepted: %s", user.log_display)
        self.activate_user(user)
        return ActivationResult(self.Result.ACCEPTED)

    def activate_user(self, user):
        ok, msg = self.validate_user_action(user, "ACTIVATE")
        if not ok:
            return ActivationResult(self.Result.ERROR, msg)

        user.is_active = True
        user.deactivated_reason = None
        user.deactivated_at = None
        user.save()
        logger.info("User activated: %s", user.log_display)
        return ActivationResult(self.Result.ACTIVATED)

    def deactivate_user(self, user, reason=''):
        ok, msg = self.validate_user_action(user, "DEACTIVATE")
        if not ok:
            return ActivationResult(self.Result.ERROR, msg)

        if user.is_active:
            user.deactivated_at = datetime.datetime.now()
        user.is_active = False
        user.deactivated_reason = reason
        user.save()
        logger.info("User deactivated: %s", user.log_display)
        return ActivationResult(self.Result.DEACTIVATED)

    def reject_user(self, user, reason):
        logger.info("Rejecting user: %s", user.log_display)
        ok, msg = self.validate_user_action(user, "REJECT")
        if not ok:
            if msg == _(astakos_messages.ACCOUNT_ALREADY_MODERATED):
                logger.warning("User already moderated: %s", user.log_display)
            elif msg == _(astakos_messages.ACCOUNT_ALREADY_ACTIVE):
                logger.warning("Cannot reject active user: %s",
                               user.log_display)
            elif msg == _(astakos_messages.ACCOUNT_NOT_VERIFIED):
                logger.warning("Cannot reject unverified user: %s",
                               user.log_display)
            return ActivationResult(self.Result.ERROR, msg)

        user.moderated = True
        user.moderated_at = datetime.datetime.now()
        user.moderated_data = json.dumps(user.__dict__,
                                         default=lambda obj:
                                         unicode(obj))
        user.is_rejected = True
        user.rejected_reason = reason
        user.save()
        logger.info("User rejected: %s", user.log_display)
        return ActivationResult(self.Result.REJECTED)

    def handle_registration(self, user, email_verified=False):
        logger.info("Handling new user registration: %s", user.log_display)
        return self.prepare_user(user, email_verified=email_verified)

    def handle_verification(self, user, activation_code):
        logger.info("Handling user email verification: %s", user.log_display)
        return self.verify_user(user, activation_code)

    def handle_moderation(self, user, accept=True, reject_reason=None):
        logger.info("Handling user moderation (%r): %s",
                    accept, user.log_display)
        if accept:
            return self.accept_user(user)
        else:
            return self.reject_user(user, reject_reason)

    def send_user_verification_email(self, user):
        ok, _ = self.validate_user_action(user, "SEND_VERIFICATION_MAIL")
        if not ok:
            raise Exception("User email already verified.")

        # invalidate previous code
        user.renew_verification_code()
        user.save()
        user_utils.send_verification(user)
        user.activation_sent = datetime.datetime.now()
        user.save()

    def send_result_notifications(self, result, user):
        """
        Send corresponding notifications based on the status of activation
        result.

        Result.PENDING_VERIFICATION
            * Send user the email verification url

        Result.PENDING_MODERATION
            * Notify admin for account moderation

        Result.ACCEPTED
            * Send user greeting notification

        Result.REJECTED
            * Send nothing
        """
        if result.status == self.Result.PENDING_VERIFICATION:
            logger.info("Sending notifications for user"
                        " creation: %s", user.log_display)
            # email user that contains the activation link
            self.send_user_verification_email(user)
            # TODO: optionally notify admins for new accounts

        if result.status == self.Result.PENDING_MODERATION:
            logger.info("Sending notifications for user"
                        " verification: %s", user.log_display)
            user_utils.send_account_pending_moderation_notification(
                user,
                self.pending_moderation_template_name)
            # TODO: notify user

        if result.status == self.Result.ACCEPTED:
            logger.info("Sending notifications for user"
                        " moderation: %s", user.log_display)
            user_utils.send_account_activated_notification(
                user,
                self.activated_email_template_name)
            user_utils.send_greeting(user,
                                     self.greeting_template_name)
            # TODO: notify admins

        if result.status == self.Result.REJECTED:
            logger.info("Sending notifications for user"
                        " rejection: %s", user.log_display)
            # TODO: notify user and admins


class InvitationsBackend(ActivationBackend):
    """
    A activation backend which implements the following workflow: a user
    supplies the necessary registation information, if the request contains a
    valid inivation code the user is automatically activated otherwise an
    inactive user account is created and the user is going to receive an email
    as soon as an administrator activates his/her account.
    """

    def get_signup_form(self, invitation, provider='local', initial_data=None,
                        instance=None):
        """
        Returns a form instance of the relevant class

        raises Invitation.DoesNotExist and ValueError if invitation is consumed
        or invitation username is reserved.
        """
        self.invitation = invitation
        prefix = 'Invited' if invitation else ''
        main = provider.capitalize() if provider == 'local' else 'ThirdParty'
        suffix = 'UserCreationForm'
        formclass = getattr(forms, '%s%s%s' % (prefix, main, suffix))
        return formclass(initial_data, instance=instance)

    def get_signup_initial_data(self, request, provider):
        """
        Returns the necassary activation form depending the user is invited or
        not.

        Throws Invitation.DoesNotExist in case ``code`` is not valid.
        """
        invitation = self.invitation
        initial_data = None
        if request.method == 'GET':
            if invitation:
                first, last = models.split_realname(invitation.realname)
                initial_data = {'email': invitation.username,
                                'inviter': invitation.inviter.realname,
                                'first_name': first,
                                'last_name': last,
                                'provider': provider}
        else:
            if provider == request.POST.get('provider', ''):
                initial_data = request.POST
        return initial_data

    def _is_preaccepted(self, user):
        """
        Extends _is_preaccepted and if there is a valid, not-consumed
        invitation code for the specific user returns True else returns False.
        """
        preaccepted = super(InvitationsBackend, self)._is_preaccepted(user)
        if preaccepted:
            return preaccepted
        invitation = self.invitation
        if not invitation:
            if not self.moderation_enabled:
                return 'auto_moderation'
        if invitation.username == user.email and not invitation.is_consumed:
            invitation.consume()
            return 'invitation'
        return False


class SimpleBackend(ActivationBackend):
    """
    The common activation backend.
    """

# shortcut
ActivationResultStatus = ActivationBackend.Result


class ActivationResult(object):

    MESSAGE_BY_STATUS = {
        ActivationResultStatus.PENDING_VERIFICATION:
        _(astakos_messages.VERIFICATION_SENT),
        ActivationResultStatus.PENDING_MODERATION:
        _(astakos_messages.NOTIFICATION_SENT),
        ActivationResultStatus.ACCEPTED:
        _(astakos_messages.ACCOUNT_ACTIVATED),
        ActivationResultStatus.ACTIVATED:
        _(astakos_messages.ACCOUNT_ACTIVATED),
        ActivationResultStatus.DEACTIVATED:
        _(astakos_messages.ACCOUNT_DEACTIVATED),
        ActivationResultStatus.ERROR:
        _(astakos_messages.GENERIC_ERROR)
    }

    STATUS_DISPLAY = {
        ActivationResultStatus.PENDING_VERIFICATION: 'PENDING_VERIFICATION',
        ActivationResultStatus.PENDING_MODERATION: 'PENDING_MODERATION',
        ActivationResultStatus.ACCEPTED: 'ACCEPTED',
        ActivationResultStatus.ACTIVATED: 'ACTIVATED',
        ActivationResultStatus.DEACTIVATED: 'DEACTIVATED',
        ActivationResultStatus.ERROR: 'ERROR'
    }

    def __init__(self, status, message=None):
        if message is None:
            message = self.MESSAGE_BY_STATUS.get(status)

        self.message = message
        self.status = status

    def status_display(self):
        return self.STATUS_DISPLAY.get(self.status)

    def __repr__(self):
        return "ActivationResult [%s]: %s" % (self.status_display(),
                                              self.message)

    def is_error(self):
        return self.status == ActivationResultStatus.ERROR

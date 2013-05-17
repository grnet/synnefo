# Copyright 2011 GRNET S.A. All rights reserved.
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

from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from astakos.im.models import AstakosUser
from astakos.im.util import get_invitation
from astakos.im import functions
from astakos.im import settings
from astakos.im import forms

from astakos.im.quotas import qh_sync_user

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
    >>> # it is wise to not instantiate a backend class directly but use
    >>> # get_backend method instead.
    >>> backend = get_backend()
    >>> formCls = backend.get_signup_form(request.POST)
    >>> if form.is_valid():
    >>>     user = form.save(commit=False)
    >>>     # this creates auth provider objects
    >>>     form.store_user(user)
    >>>     activation = backend.handle_registration(user)
    >>>     # activation.status is one of backend.Result.{*} activation result
    >>>     # types
    >>>
    >>>     # sending activation notifications is not done automatically
    >>>     # we need to call send_result_notifications
    >>>     backend.send_result_notifications(activation)
    >>>     return HttpResponse(activation.message)
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
        """
        Initialization of a newly registered user. The method sets email
        verification code. If email_verified is set to True we automatically
        process user through the verification step.
        """
        logger.info("Initializing user registration %s", user.log_display)

        if not email_verified:
            email_verified = settings.SKIP_EMAIL_VERIFICATION

        user.renew_verification_code()
        user.save()

        if email_verified:
            logger.info("Auto verifying user email. %s",
                        user.log_display)
            return self.verify_user(user,
                                    user.verification_code)

        return ActivationResult(self.Result.PENDING_VERIFICATION)

    def verify_user(self, user, verification_code):
        """
        Process user verification using provided verification_code. This
        should take place in user activation view. If no moderation is enabled
        we automatically process user through activation process.
        """
        logger.info("Verifying user: %s", user.log_display)

        if user.email_verified:
            logger.warning("User email already verified: %s",
                           user.log_display)
            msg = astakos_messages.ACCOUNT_ALREADY_VERIFIED
            return ActivationResult(self.Result.ERROR, msg)

        if user.verification_code and \
                user.verification_code == verification_code:
            user.email_verified = True
            user.verified_at = datetime.datetime.now()
            # invalidate previous code
            user.renew_verification_code()
            user.save()
            logger.info("User email verified: %s", user.log_display)
        else:
            logger.error("User email verification failed "
                         "(invalid verification code): %s", user.log_display)
            msg = astakos_messages.VERIFICATION_FAILED
            return ActivationResult(self.Result.ERROR, msg)

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
        if user.moderated and user.is_active:
            logger.warning("User already accepted, moderation"
                           " skipped: %s", user.log_display)
            msg = _(astakos_messages.ACCOUNT_ALREADY_MODERATED)
            return ActivationResult(self.Result.ERROR, msg)

        if not user.email_verified:
            logger.warning("Cannot accept unverified user: %s",
                           user.log_display)
            msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
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
                                         str(obj))
        user.save()
        qh_sync_user(user)

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
        if not user.email_verified:
            msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
            return ActivationResult(self.Result.ERROR, msg)

        if not user.moderated:
            msg = _(astakos_messages.ACCOUNT_NOT_MODERATED)
            return ActivationResult(self.Result.ERROR, msg)

        if user.is_rejected:
            msg = _(astakos_messages.ACCOUNT_REJECTED)
            return ActivationResult(self.Result.ERROR, msg)

        if user.is_active:
            msg = _(astakos_messages.ACCOUNT_ALREADY_ACTIVE)
            return ActivationResult(self.Result.ERROR, msg)

        user.is_active = True
        user.deactivated_reason = None
        user.deactivated_at = None
        user.save()
        logger.info("User activated: %s", user.log_display)
        return ActivationResult(self.Result.ACTIVATED)

    def deactivate_user(self, user, reason=''):
        user.is_active = False
        user.deactivated_reason = reason
        if user.is_active:
            user.deactivated_at = datetime.datetime.now()
        user.save()
        logger.info("User deactivated: %s", user.log_display)
        return ActivationResult(self.Result.DEACTIVATED)

    def reject_user(self, user, reason):
        logger.info("Rejecting user: %s", user.log_display)
        if user.moderated:
            logger.warning("User already moderated: %s", user.log_display)
            msg = _(astakos_messages.ACCOUNT_ALREADY_MODERATED)
            return ActivationResult(self.Result.ERROR, msg)

        if user.is_active:
            logger.warning("Cannot reject unverified user: %s",
                           user.log_display)
            msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
            return ActivationResult(self.Result.ERROR, msg)

        if not user.email_verified:
            logger.warning("Cannot reject unverified user: %s",
                           user.log_display)
            msg = _(astakos_messages.ACCOUNT_NOT_VERIFIED)
            return ActivationResult(self.Result.ERROR, msg)

        user.moderated = True
        user.moderated_at = datetime.datetime.now()
        user.moderated_data = json.dumps(user.__dict__,
                                         default=lambda obj:
                                         str(obj))
        user.is_rejected = True
        user.rejected_reason = reason
        logger.info("User rejected: %s", user.log_display)
        return ActivationResult(self.Result.REJECTED)

    def handle_registration(self, user, email_verified=False):
        logger.info("Handling new user registration: %s", user.log_display)
        return self.prepare_user(user, email_verified=email_verified)

    def handle_verification(self, user, activation_code):
        logger.info("Handling user email verirfication: %s", user.log_display)
        return self.verify_user(user, activation_code)

    def handle_moderation(self, user, accept=True, reject_reason=None):
        logger.info("Handling user moderation (%r): %s",
                    accept, user.log_display)
        if accept:
            return self.accept_user(user)
        else:
            return self.reject_user(user, reject_reason)

    def send_user_verification_email(self, user):
        if user.is_active:
            raise Exception("User already active")

        # invalidate previous code
        user.renew_verification_code()
        user.save()
        functions.send_verification(user)
        user.activation_sent = datetime.datetime.now()
        user.save()

    def send_result_notifications(self, result, user):
        """
        Send corresponding notifications based on the status of activation
        result.

        Result.PENDING_VERIRFICATION
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
            functions.send_account_pending_moderation_notification(user,
                                        self.pending_moderation_template_name)
            # TODO: notify user

        if result.status == self.Result.ACCEPTED:
            logger.info("Sending notifications for user"
                        " moderation: %s", user.log_display)
            functions.send_account_activated_notification(user,
                                         self.activated_email_template_name)
            functions.send_greeting(user,
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
                # create a tmp user with the invitation realname
                # to extract first and last name
                u = AstakosUser(realname=invitation.realname)
                initial_data = {'email': invitation.username,
                                'inviter': invitation.inviter.realname,
                                'first_name': u.first_name,
                                'last_name': u.last_name,
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

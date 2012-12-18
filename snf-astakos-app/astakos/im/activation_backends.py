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
from astakos.im.functions import (
    send_activation, send_account_creation_notification, activate)
from astakos.im.settings import (
    INVITATIONS_ENABLED, RE_USER_EMAIL_PATTERNS)
from astakos.im import settings as astakos_settings
from astakos.im.forms import *

import astakos.im.messages as astakos_messages

import logging
import re

logger = logging.getLogger(__name__)


def get_backend(request):
    """
    Returns an instance of an activation backend,
    according to the INVITATIONS_ENABLED setting
    (if True returns ``astakos.im.activation_backends.InvitationsBackend`` and if False
    returns ``astakos.im.activation_backends.SimpleBackend``).

    If the backend cannot be located ``django.core.exceptions.ImproperlyConfigured``
    is raised.
    """
    module = 'astakos.im.activation_backends'
    prefix = 'Invitations' if INVITATIONS_ENABLED else 'Simple'
    backend_class_name = '%sBackend' % prefix
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured(
            'Error loading activation backend %s: "%s"' % (module, e))
    try:
        backend_class = getattr(mod, backend_class_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a activation backend named "%s"' % (module, backend_class_name))
    return backend_class(request)


class ActivationBackend(object):
    def __init__(self, request):
        self.request = request

    def _is_preaccepted(self, user):
        # return True if user email matches specific patterns
        for pattern in RE_USER_EMAIL_PATTERNS:
            if re.match(pattern, user.email):
                return True
        return False

    def get_signup_form(self, provider='local', instance=None):
        """
        Returns a form instance of the relevant class
        """
        main = provider.capitalize() if provider == 'local' else 'ThirdParty'
        suffix = 'UserCreationForm'
        formclass = '%s%s' % (main, suffix)
        request = self.request
        initial_data = None
        if request.method == 'POST':
            if provider == request.POST.get('provider', ''):
                initial_data = request.POST
        return globals()[formclass](initial_data, instance=instance, request=request)

    def handle_activation(
        self, user, activation_template_name='im/activation_email.txt',
        greeting_template_name='im/welcome_email.txt',
        admin_email_template_name='im/account_creation_notification.txt',
        helpdesk_email_template_name='im/helpdesk_notification.txt'
    ):
        """
        If the user is already active returns immediately.
        If the user is preaccepted and the email is verified, the account is
        activated automatically. Otherwise, if the email is not verified,
        it sends a verification email to the user.
        If the user is not preaccepted, it sends an email to the administrators
        and informs the user that the account is pending activation.
        """
        try:
            if user.is_active:
                return RegistationCompleted()

            if self._is_preaccepted(user):
                if user.email_verified:
                    activate(
                        user,
                        greeting_template_name,
                        helpdesk_email_template_name
                    )
                    return RegistationCompleted()
                else:
                    send_activation(
                        user,
                        activation_template_name
                    )
                    return VerificationSent()
            else:
                send_account_creation_notification(
                    template_name=admin_email_template_name,
                    dictionary={'user': user.__dict__, 'group_creation': True}
                )
                return NotificationSent()
        except BaseException, e:
            logger.exception(e)
            raise e


class InvitationsBackend(ActivationBackend):
    """
    A activation backend which implements the following workflow: a user
    supplies the necessary registation information, if the request contains a valid
    inivation code the user is automatically activated otherwise an inactive user
    account is created and the user is going to receive an email as soon as an
    administrator activates his/her account.
    """

    def get_signup_form(self, provider='local', instance=None):
        """
        Returns a form instance of the relevant class

        raises Invitation.DoesNotExist and ValueError if invitation is consumed
        or invitation username is reserved.
        """
        self.invitation = get_invitation(self.request)
        invitation = self.invitation
        initial_data = self.get_signup_initial_data(provider)
        prefix = 'Invited' if invitation else ''
        main = provider.capitalize() if provider == 'local' else 'ThirdParty'
        suffix = 'UserCreationForm'
        formclass = '%s%s%s' % (prefix, main, suffix)
        return globals()[formclass](initial_data, instance=instance, request=self.request)

    def get_signup_initial_data(self, provider):
        """
        Returns the necassary activation form depending the user is invited or not

        Throws Invitation.DoesNotExist in case ``code`` is not valid.
        """
        request = self.request
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
        Extends _is_preaccepted and if there is a valid, not-consumed invitation
        code for the specific user returns True else returns False.
        """
        if super(InvitationsBackend, self)._is_preaccepted(user):
            return True
        invitation = self.invitation
        if not invitation:
            return not astakos_settings.MODERATION_ENABLED
        if invitation.username == user.email and not invitation.is_consumed:
            invitation.consume()
            return True
        return False


class SimpleBackend(ActivationBackend):
    """
    A activation backend which implements the following workflow: a user
    supplies the necessary registation information, an incative user account is
    created and receives an email in order to activate his/her account.
    """
    def _is_preaccepted(self, user):
        if super(SimpleBackend, self)._is_preaccepted(user):
            return True
        if astakos_settings.MODERATION_ENABLED:
            return False
        return True


class ActivationResult(object):
    def __init__(self, message):
        self.message = message


class VerificationSent(ActivationResult):
    def __init__(self):
        message = _(astakos_messages.VERIFICATION_SENT)
        super(VerificationSent, self).__init__(message)

class NotificationSent(ActivationResult):
    def __init__(self):
        message = _(astakos_messages.NOTIFICATION_SENT)
        super(NotificationSent, self).__init__(message)


class RegistationCompleted(ActivationResult):
    def __init__(self):
        message = _(astakos_messages.REGISTRATION_COMPLETED)
        super(RegistationCompleted, self).__init__(message)

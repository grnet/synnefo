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
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.db import transaction

from urlparse import urljoin

from astakos.im.models import AstakosUser, Invitation
from astakos.im.forms import *
from astakos.im.util import get_invitation
from astakos.im.functions import send_verification, send_admin_notification, activate
from astakos.im.settings import INVITATIONS_ENABLED, DEFAULT_CONTACT_EMAIL, DEFAULT_FROM_EMAIL, MODERATION_ENABLED, SITENAME, BASEURL, DEFAULT_ADMIN_EMAIL, RE_USER_EMAIL_PATTERNS

import socket
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
    backend_class_name = '%sBackend' %prefix
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error loading activation backend %s: "%s"' % (module, e))
    try:
        backend_class = getattr(mod, backend_class_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a activation backend named "%s"' % (module, attr))
    return backend_class(request)

class SignupBackend(object):
    def _is_preaccepted(self, user):
        # return True if user email matches specific patterns
        for pattern in RE_USER_EMAIL_PATTERNS:
            if re.match(pattern, user.email):
                return True
        return False

class InvitationsBackend(SignupBackend):
    """
    A activation backend which implements the following workflow: a user
    supplies the necessary registation information, if the request contains a valid
    inivation code the user is automatically activated otherwise an inactive user
    account is created and the user is going to receive an email as soon as an
    administrator activates his/her account.
    """
    def __init__(self, request):
        """
        raises Invitation.DoesNotExist and ValueError if invitation is consumed
        or invitation username is reserved.
        """
        self.request = request
        self.invitation = get_invitation(request)
        super(InvitationsBackend, self).__init__()

    def get_signup_form(self, provider='local'):
        """
        Returns the form class name
        """
        invitation = self.invitation
        initial_data = self.get_signup_initial_data(provider)
        prefix = 'Invited' if invitation else ''
        main = provider.capitalize()
        suffix  = 'UserCreationForm'
        formclass = '%s%s%s' % (prefix, main, suffix)
        ip = self.request.META.get('REMOTE_ADDR',
                self.request.META.get('HTTP_X_REAL_IP', None))
        return globals()[formclass](initial_data, ip=ip)

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
                u = AstakosUser(realname = invitation.realname)
                print '>>>', invitation, invitation.inviter
                initial_data = {'email':invitation.username,
                                'inviter':invitation.inviter.realname,
                                'first_name':u.first_name,
                                'last_name':u.last_name}
        else:
            if provider == request.POST.get('provider', ''):
                initial_data = request.POST
        return initial_data

    def _is_preaccepted(self, user):
        """
        If there is a valid, not-consumed invitation code for the specific user
        returns True else returns False.
        """
        if super(InvitationsBackend, self)._is_preaccepted(user):
            return True
        invitation = self.invitation
        if not invitation:
            return False
        if invitation.username == user.email and not invitation.is_consumed:
            invitation.consume()
            return True
        return False

    def handle_activation(self, user, verification_template_name='im/activation_email.txt', greeting_template_name='im/welcome_email.txt', admin_email_template_name='im/admin_notification.txt'):
        """
        Initially creates an inactive user account. If the user is preaccepted
        (has a valid invitation code) the user is activated and if the request
        param ``next`` is present redirects to it.
        In any other case the method returns the action status and a message.

        The method uses commit_manually decorator in order to ensure the user
        will be created only if the procedure has been completed successfully.
        """
        try:
            if user.is_active:
                return RegistationCompleted()
            if self._is_preaccepted(user):
                if user.email_verified:
                    activate(user, greeting_template_name)
                    return RegistationCompleted()
                else:
                    send_verification(user, verification_template_name)
                    return VerificationSent()
            else:
                send_admin_notification(user, admin_email_template_name)
                return NotificationSent()
        except Invitation.DoesNotExist, e:
            raise InvitationCodeError()
        except BaseException, e:
            logger.exception(e)
            raise e

class SimpleBackend(SignupBackend):
    """
    A activation backend which implements the following workflow: a user
    supplies the necessary registation information, an incative user account is
    created and receives an email in order to activate his/her account.
    """
    def __init__(self, request):
        self.request = request
        super(SimpleBackend, self).__init__()

    def get_signup_form(self, provider='local'):
        """
        Returns the form class name
        """
        main = provider.capitalize() if provider == 'local' else 'ThirdParty'
        suffix  = 'UserCreationForm'
        formclass = '%s%s' % (main, suffix)
        request = self.request
        initial_data = None
        if request.method == 'POST':
            if provider == request.POST.get('provider', ''):
                initial_data = request.POST
        ip = self.request.META.get('REMOTE_ADDR',
                self.request.META.get('HTTP_X_REAL_IP', None))
        return globals()[formclass](initial_data, ip=ip)
    
    def _is_preaccepted(self, user):
        if super(SimpleBackend, self)._is_preaccepted(user):
            return True
        if MODERATION_ENABLED:
            return False
        return True
    
    def handle_activation(self, user, email_template_name='im/activation_email.txt', admin_email_template_name='im/admin_notification.txt'):
        """
        Creates an inactive user account and sends a verification email.

        The method uses commit_manually decorator in order to ensure the user
        will be created only if the procedure has been completed successfully.

        ** Arguments **

        ``email_template_name``
            A custom template for the verification email body to use. This is
            optional; if not specified, this will default to
            ``im/activation_email.txt``.

        ** Templates **
            im/activation_email.txt or ``email_template_name`` keyword argument

        ** Settings **

        * DEFAULT_CONTACT_EMAIL: service support email
        * DEFAULT_FROM_EMAIL: from email
        """
        try:
            if user.is_active:
                return RegistrationCompeted()
            if not self._is_preaccepted(user):
                send_admin_notification(user, admin_email_template_name)
                return NotificationSent()
            else:
                send_verification(user, email_template_name)
                return VerificationSend()
        except SendEmailError, e:
            transaction.rollback()
            raise e
        except BaseException, e:
            logger.exception(e)
            raise e
        else:
            transaction.commit()

class ActivationResult(object):
    def __init__(self, message):
        self.message = message

class VerificationSent(ActivationResult):
    def __init__(self):
        message = _('Verification sent.')
        super(VerificationSent, self).__init__(message)

class NotificationSent(ActivationResult):
    def __init__(self):
        message = _('Your request for an account was successfully received and is now pending \
                    approval. You will be notified by email in the next few days. Thanks for \
                    your interest in ~okeanos! The GRNET team.')
        super(NotificationSent, self).__init__(message)

class RegistationCompleted(ActivationResult):
    def __init__(self):
        message = _('Registration completed. You can now login.')
        super(RegistationCompleted, self).__init__(message)
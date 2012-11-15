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

import logging
import socket

from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.template import Context, loader
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpRequest

from urllib import quote
from urlparse import urljoin
from smtplib import SMTPException
from datetime import datetime
from functools import wraps

from astakos.im.settings import DEFAULT_CONTACT_EMAIL, DEFAULT_FROM_EMAIL, \
    SITENAME, BASEURL, DEFAULT_ADMIN_EMAIL, LOGGING_LEVEL, \
    VERIFICATION_EMAIL_SUBJECT, ADMIN_NOTIFICATION_EMAIL_SUBJECT, \
    HELPDESK_NOTIFICATION_EMAIL_SUBJECT, INVITATION_EMAIL_SUBJECT, \
    GREETING_EMAIL_SUBJECT, FEEDBACK_EMAIL_SUBJECT, EMAIL_CHANGE_EMAIL_SUBJECT
from astakos.im.models import Invitation, AstakosUser

logger = logging.getLogger(__name__)

def logged(func, msg):
    @wraps(func)
    def with_logging(*args, **kwargs):
        email = ''
        user = None
        if len(args) == 2 and isinstance(args[1], AstakosUser):
            user = args[1]
        elif len(args) == 1 and isinstance(args[0], HttpRequest):
            request = args[0]
            user = request.user
        email = user.email if user and user.is_authenticated() else ''
        r = func(*args, **kwargs)
        if LOGGING_LEVEL:
            logger._log(LOGGING_LEVEL, msg % email, [])
        return r
    return with_logging

login = logged(auth_login, '%s logged in.')
logout = logged(auth_logout, '%s logged out.')

def send_verification(user, template_name='im/activation_email.txt'):
    """
    Send email to user to verify his/her email and activate his/her account.
    
    Raises SendVerificationError
    """
    url = '%s?auth=%s&next=%s' % (urljoin(BASEURL, reverse('astakos.im.views.activate')),
                                    quote(user.auth_token),
                                    quote(urljoin(BASEURL, reverse('astakos.im.views.index'))))
    message = render_to_string(template_name, {
            'user': user,
            'url': url,
            'baseurl': BASEURL,
            'site_name': SITENAME,
            'support': DEFAULT_CONTACT_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    try:
        send_mail(_(VERIFICATION_EMAIL_SUBJECT), message, sender, [user.email])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendVerificationError()
    else:
        msg = 'Sent activation %s' % user.email
        logger._log(LOGGING_LEVEL, msg, [])

def send_activation(user, template_name='im/activation_email.txt'):
    send_verification(user, template_name)
    user.activation_sent = datetime.now()
    user.save()

def send_admin_notification(user, template_name='im/admin_notification.txt'):
    """
    Send email to DEFAULT_ADMIN_EMAIL to notify for a new user registration.
    
    Raises SendNotificationError
    """
    if not DEFAULT_ADMIN_EMAIL:
        return
    message = render_to_string(template_name, {
            'user': user,
            'baseurl': BASEURL,
            'site_name': SITENAME,
            'support': DEFAULT_CONTACT_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    try:
        send_mail(_(ADMIN_NOTIFICATION_EMAIL_SUBJECT) % {'user': user.email}, message, sender, [DEFAULT_ADMIN_EMAIL])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendNotificationError()
    else:
        msg = 'Sent admin notification for user %s' % user.email
        logger._log(LOGGING_LEVEL, msg, [])

def send_helpdesk_notification(user, template_name='im/helpdesk_notification.txt'):
    """
    Send email to DEFAULT_CONTACT_EMAIL to notify for a new user activation.
    
    Raises SendNotificationError
    """
    if not DEFAULT_CONTACT_EMAIL:
        return
    message = render_to_string(template_name, {
            'user': user,
            'baseurl': BASEURL,
            'site_name': SITENAME,
            'support': DEFAULT_ADMIN_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    try:
        send_mail(_(HELPDESK_NOTIFICATION_EMAIL_SUBJECT) % {'user': user.email}, message, sender, [DEFAULT_CONTACT_EMAIL])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendNotificationError()
    else:
        msg = 'Sent helpdesk admin notification for user %s' % user.email
        logger._log(LOGGING_LEVEL, msg, [])

def send_invitation(invitation, template_name='im/invitation.txt'):
    """
    Send invitation email.
    
    Raises SendInvitationError
    """
    subject = _(INVITATION_EMAIL_SUBJECT)
    url = '%s?code=%d' % (urljoin(BASEURL, reverse('astakos.im.views.index')), invitation.code)
    message = render_to_string('im/invitation.txt', {
                'invitation': invitation,
                'url': url,
                'baseurl': BASEURL,
                'site_name': SITENAME,
                'support': DEFAULT_CONTACT_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    try:
        send_mail(subject, message, sender, [invitation.username])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendInvitationError()
    else:
        msg = 'Sent invitation %s' % invitation
        logger._log(LOGGING_LEVEL, msg, [])

def send_greeting(user, email_template_name='im/welcome_email.txt'):
    """
    Send welcome email.
    
    Raises SMTPException, socket.error
    """
    subject = _(GREETING_EMAIL_SUBJECT)
    message = render_to_string(email_template_name, {
                'user': user,
                'url': urljoin(BASEURL, reverse('astakos.im.views.index')),
                'baseurl': BASEURL,
                'site_name': SITENAME,
                'support': DEFAULT_CONTACT_EMAIL})
    sender = DEFAULT_FROM_EMAIL
    try:
        send_mail(subject, message, sender, [user.email])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendGreetingError()
    else:
        msg = 'Sent greeting %s' % user.email
        logger._log(LOGGING_LEVEL, msg, [])

def send_feedback(msg, data, user, email_template_name='im/feedback_mail.txt'):
    subject = _(FEEDBACK_EMAIL_SUBJECT)
    from_email = user.email
    recipient_list = [DEFAULT_CONTACT_EMAIL]
    content = render_to_string(email_template_name, {
        'message': msg,
        'data': data,
        'user': user})
    try:
        send_mail(subject, content, from_email, recipient_list)
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendFeedbackError()
    else:
        msg = 'Sent feedback from %s' % user.email
        logger._log(LOGGING_LEVEL, msg, [])

def send_change_email(ec, request, email_template_name='registration/email_change_email.txt'):
    try:
        url = reverse('email_change_confirm',
                      kwargs={'activation_key':ec.activation_key})
        url = request.build_absolute_uri(url)
        t = loader.get_template(email_template_name)
        c = {'url': url, 'site_name': SITENAME}
        from_email = DEFAULT_FROM_EMAIL
        send_mail(_(EMAIL_CHANGE_EMAIL_SUBJECT),
            t.render(Context(c)), from_email, [ec.new_email_address])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise ChangeEmailError()
    else:
        msg = 'Sent change email for %s' % ec.user.email
        logger._log(LOGGING_LEVEL, msg, [])

def activate(user, email_template_name='im/welcome_email.txt',
                helpdesk_email_template_name='im/helpdesk_notification.txt', verify_email=False):
    """
    Activates the specific user and sends email.
    
    Raises SendGreetingError, ValidationError
    """
    user.is_active = True
    if verify_email:
        user.email_verified = True
    user.save()
    send_helpdesk_notification(user, helpdesk_email_template_name)
    send_greeting(user, email_template_name)

def invite(invitation, inviter, email_template_name='im/welcome_email.txt'):
    """
    Send an invitation email and upon success reduces inviter's invitation by one.
    
    Raises SendInvitationError
    """
    invitation.inviter = inviter
    invitation.save()
    send_invitation(invitation, email_template_name)
    inviter.invitations = max(0, inviter.invitations - 1)
    inviter.save()

def set_user_credibility(email, has_credits):
    try:
        user = AstakosUser.objects.get(email=email, is_active=True)
        user.has_credits = has_credits
        user.save()
    except AstakosUser.DoesNotExist, e:
        logger.exception(e)
    except ValidationError, e:
        logger.exception(e)

class SendMailError(Exception):
    pass

class SendAdminNotificationError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send notification')
        super(SendAdminNotificationError, self).__init__()

class SendVerificationError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send verification')
        super(SendVerificationError, self).__init__()

class SendInvitationError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send invitation')
        super(SendInvitationError, self).__init__()

class SendGreetingError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send greeting')
        super(SendGreetingError, self).__init__()

class SendFeedbackError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send feedback')
        super(SendFeedbackError, self).__init__()

class ChangeEmailError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send change email')
        super(ChangeEmailError, self).__init__()

class SendNotificationError(SendMailError):
    def __init__(self):
        self.message = _('Failed to send notification email')
        super(SendNotificationError, self).__init__()

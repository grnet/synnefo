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
from django.core.mail import send_mail, get_connection
from django.core.urlresolvers import reverse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.utils.translation import ugettext as _

from synnefo_branding.utils import render_to_string
from synnefo.lib import join_urls

from astakos.im import settings
from astakos.im.models import Invitation
import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


def login(request, user):
    auth_login(request, user)
    from astakos.im.models import SessionCatalog
    SessionCatalog(
        session_key=request.session.session_key,
        user=user
    ).save()
    logger.info('%s logged in.', user.log_display)


def logout(request, *args, **kwargs):
    user = request.user
    auth_logout(request, *args, **kwargs)
    user.delete_online_access_tokens()
    logger.info('%s logged out.', user.log_display)


def invite(inviter, email, realname):
    inv = Invitation(inviter=inviter, username=email, realname=realname)
    inv.save()
    send_invitation(inv)
    inviter.invitations = max(0, inviter.invitations - 1)
    inviter.save()


def send_plain(user, sender=settings.SERVER_EMAIL,
               subject=_(astakos_messages.PLAIN_EMAIL_SUBJECT),
               template_name='im/plain_email.txt', text=None):
    """Send mail to user with fully customizable sender, subject and body.

    If the function is provided with a `template name`, then it will be used
    for rendering the mail. Any additional text should be provided in the
    `text` parameter and it will be included in the main body of the mail.

    If the function is not provided with a `template name`, then it will use
    the string provided in the `text` parameter as the mail body.
    """
    if not template_name:
        message = text
    else:
        message = render_to_string(template_name, {
                                   'user': user,
                                   'text': text,
                                   'baseurl': settings.BASE_URL,
                                   'support': settings.CONTACT_EMAIL})

    send_mail(subject, message, sender, [user.email],
              connection=get_connection())
    logger.info("Sent plain email to user: %s", user.log_display)


def send_verification(user, template_name='im/activation_email.txt'):
    """
    Send email to user to verify his/her email and activate his/her account.
    """
    index_url = reverse('index', urlconf="synnefo.webproject.urls")
    url = join_urls(settings.BASE_HOST,
                    user.get_activation_url(nxt=index_url))
    message = render_to_string(template_name, {
                               'user': user,
                               'url': url,
                               'baseurl': settings.BASE_URL,
                               'support': settings.CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    send_mail(_(astakos_messages.VERIFICATION_EMAIL_SUBJECT), message, sender,
              [user.email],
              connection=get_connection())
    logger.info("Sent user verification email: %s", user.log_display)


def send_account_pending_moderation_notification(
        user,
        template_name='im/account_pending_moderation_notification.txt'):
    """
    Notify 'ACCOUNT_PENDING_MODERATION_RECIPIENTS' that a new user has verified
    his email address and moderation step is required to activate his account.
    """
    subject = (_(astakos_messages.ACCOUNT_CREATION_SUBJECT) %
               {'user': user.email})
    message = render_to_string(template_name, {'user': user})
    sender = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in
                      settings.ACCOUNT_PENDING_MODERATION_RECIPIENTS]
    send_mail(subject, message, sender, recipient_list,
              connection=get_connection())
    msg = 'Sent admin notification (account creation) for user %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.log_display)


def send_account_activated_notification(
        user,
        template_name='im/account_activated_notification.txt'):
    """
    Send email to ACCOUNT_ACTIVATED_RECIPIENTS list to notify that a new
    account has been accepted and activated.
    """
    message = render_to_string(
        template_name,
        {'user': user}
    )
    sender = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in
                      settings.ACCOUNT_ACTIVATED_RECIPIENTS]
    send_mail(_(astakos_messages.HELPDESK_NOTIFICATION_EMAIL_SUBJECT) %
              {'user': user.email},
              message, sender, recipient_list, connection=get_connection())
    msg = 'Sent helpdesk admin notification for %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.email)


def send_invitation(invitation, template_name='im/invitation.txt'):
    """
    Send invitation email.
    """
    subject = _(astakos_messages.INVITATION_EMAIL_SUBJECT)
    index_url = reverse('index', urlconf="synnefo.webproject.urls")
    url = '%s?code=%d' % (join_urls(settings.BASE_HOST, index_url,
                                    invitation.code))
    message = render_to_string(template_name, {
                               'invitation': invitation,
                               'url': url,
                               'baseurl': settings.BASE_URL,
                               'support': settings.CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    send_mail(subject, message, sender, [invitation.username],
              connection=get_connection())
    msg = 'Sent invitation %s'
    logger.log(settings.LOGGING_LEVEL, msg, invitation)
    inviter_invitations = invitation.inviter.invitations
    invitation.inviter.invitations = max(0, inviter_invitations - 1)
    invitation.inviter.save()


def send_greeting(user, email_template_name='im/welcome_email.txt'):
    """
    Send welcome email to an accepted/activated user.

    Raises SMTPException, socket.error
    """
    subject = _(astakos_messages.GREETING_EMAIL_SUBJECT)
    index_url = reverse('index', urlconf="synnefo.webproject.urls")
    message = render_to_string(email_template_name, {
                               'user': user,
                               'url': join_urls(settings.BASE_HOST, index_url),
                               'baseurl': settings.BASE_URL,
                               'support': settings.CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    send_mail(subject, message, sender, [user.email],
              connection=get_connection())
    msg = 'Sent greeting %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.log_display)


def send_feedback(msg, data, user, email_template_name='im/feedback_mail.txt'):
    """Send feedback to FEEDBACK_RECIPIENTS list."""
    subject = _(astakos_messages.FEEDBACK_EMAIL_SUBJECT)
    from_email = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in settings.FEEDBACK_NOTIFICATIONS_RECIPIENTS]
    content = render_to_string(email_template_name, {
        'message': msg,
        'data': data,
        'user': user})
    send_mail(subject, content, from_email, recipient_list,
              connection=get_connection())
    msg = 'Sent feedback from %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.log_display)


def send_change_email(ec, request, email_template_name=(
                      'registration/email_change_email.txt')):
    url = ec.get_url()
    url = request.build_absolute_uri(url)
    c = {'url': url,
         'support': settings.CONTACT_EMAIL,
         'ec': ec}
    message = render_to_string(email_template_name, c)
    from_email = settings.SERVER_EMAIL
    send_mail(_(astakos_messages.EMAIL_CHANGE_EMAIL_SUBJECT), message,
              from_email,
              [ec.new_email_address], connection=get_connection())
    msg = 'Sent change email for %s'
    logger.log(settings.LOGGING_LEVEL, msg, ec.user.log_display)

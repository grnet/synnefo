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
from django.template import Context, loader
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout)
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError

from urllib import quote
from urlparse import urljoin
from smtplib import SMTPException
from datetime import datetime
from functools import wraps

from astakos.im.settings import (
    DEFAULT_CONTACT_EMAIL, SITENAME, BASEURL, LOGGING_LEVEL,
    VERIFICATION_EMAIL_SUBJECT, ACCOUNT_CREATION_SUBJECT,
    GROUP_CREATION_SUBJECT, HELPDESK_NOTIFICATION_EMAIL_SUBJECT,
    INVITATION_EMAIL_SUBJECT, GREETING_EMAIL_SUBJECT, FEEDBACK_EMAIL_SUBJECT,
    EMAIL_CHANGE_EMAIL_SUBJECT,
    PROJECT_CREATION_SUBJECT, PROJECT_APPROVED_SUBJECT,
    PROJECT_TERMINATION_SUBJECT, PROJECT_SUSPENSION_SUBJECT,
    PROJECT_MEMBERSHIP_CHANGE_SUBJECT,
    PROJECT_MEMBER_JOIN_POLICIES, PROJECT_MEMBER_LEAVE_POLICIES)
from astakos.im.notifications import build_notification, NotificationError
from astakos.im.models import (
    AstakosUser, ProjectMembership, ProjectApplication, Project,
    trigger_sync)

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


def logged(func, msg):
    @wraps(func)
    def with_logging(*args, **kwargs):
        email = ''
        user = None
        try:
            request = args[0]
            email = request.user.email
        except (KeyError, AttributeError), e:
            email = ''
        r = func(*args, **kwargs)
        if LOGGING_LEVEL:
            logger.log(LOGGING_LEVEL, msg % email)
        return r
    return with_logging


def login(request, user):
    auth_login(request, user)
    from astakos.im.models import SessionCatalog
    SessionCatalog(
        session_key=request.session.session_key,
        user=user
    ).save()

login = logged(login, '%s logged in.')
logout = logged(auth_logout, '%s logged out.')


def send_verification(user, template_name='im/activation_email.txt'):
    """
    Send email to user to verify his/her email and activate his/her account.

    Raises SendVerificationError
    """
    url = '%s?auth=%s&next=%s' % (urljoin(BASEURL, reverse('activate')),
                                  quote(user.auth_token),
                                  quote(urljoin(BASEURL, reverse('index'))))
    message = render_to_string(template_name, {
                               'user': user,
                               'url': url,
                               'baseurl': BASEURL,
                               'site_name': SITENAME,
                               'support': DEFAULT_CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    try:
        send_mail(_(VERIFICATION_EMAIL_SUBJECT), message, sender, [user.email])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendVerificationError()
    else:
        msg = 'Sent activation %s' % user.email
        logger.log(LOGGING_LEVEL, msg)


def send_activation(user, template_name='im/activation_email.txt'):
    send_verification(user, template_name)
    user.activation_sent = datetime.now()
    user.save()


def _send_admin_notification(template_name,
                             dictionary=None,
                             subject='alpha2 testing notification',):
    """
    Send notification email to settings.ADMINS.

    Raises SendNotificationError
    """
    if not settings.ADMINS:
        return
    dictionary = dictionary or {}
    message = render_to_string(template_name, dictionary)
    sender = settings.SERVER_EMAIL
    try:
        send_mail(subject,
                  message, sender, [i[1] for i in settings.ADMINS])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendNotificationError()
    else:
        msg = 'Sent admin notification for user %s' % dictionary.get('email',
                                                                     None)
        logger.log(LOGGING_LEVEL, msg)


def send_account_creation_notification(template_name, dictionary=None):
    user = dictionary.get('user', AnonymousUser())
    subject = _(ACCOUNT_CREATION_SUBJECT) % {'user':user.get('email', '')}
    return _send_admin_notification(template_name, dictionary, subject=subject)


def send_helpdesk_notification(user, template_name='im/helpdesk_notification.txt'):
    """
    Send email to DEFAULT_CONTACT_EMAIL to notify for a new user activation.

    Raises SendNotificationError
    """
    if not DEFAULT_CONTACT_EMAIL:
        return
    message = render_to_string(
        template_name,
        {'user': user}
    )
    sender = settings.SERVER_EMAIL
    try:
        send_mail(
            _(HELPDESK_NOTIFICATION_EMAIL_SUBJECT) % {'user': user.email},
            message, sender, [DEFAULT_CONTACT_EMAIL])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendNotificationError()
    else:
        msg = 'Sent helpdesk admin notification for %s' % user.email
        logger.log(LOGGING_LEVEL, msg)


def send_invitation(invitation, template_name='im/invitation.txt'):
    """
    Send invitation email.

    Raises SendInvitationError
    """
    subject = _(INVITATION_EMAIL_SUBJECT)
    url = '%s?code=%d' % (urljoin(BASEURL, reverse('index')), invitation.code)
    message = render_to_string(template_name, {
                               'invitation': invitation,
                               'url': url,
                               'baseurl': BASEURL,
                               'site_name': SITENAME,
                               'support': DEFAULT_CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    try:
        send_mail(subject, message, sender, [invitation.username])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendInvitationError()
    else:
        msg = 'Sent invitation %s' % invitation
        logger.log(LOGGING_LEVEL, msg)
        invitation.inviter.invitations = max(0, invitation.inviter.invitations - 1)
        invitation.inviter.save()


def send_greeting(user, email_template_name='im/welcome_email.txt'):
    """
    Send welcome email.

    Raises SMTPException, socket.error
    """
    subject = _(GREETING_EMAIL_SUBJECT)
    message = render_to_string(email_template_name, {
                               'user': user,
                               'url': urljoin(BASEURL, reverse('index')),
                               'baseurl': BASEURL,
                               'site_name': SITENAME,
                               'support': DEFAULT_CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    try:
        send_mail(subject, message, sender, [user.email])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendGreetingError()
    else:
        msg = 'Sent greeting %s' % user.email
        logger.log(LOGGING_LEVEL, msg)


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
        logger.log(LOGGING_LEVEL, msg)


def send_change_email(
    ec, request, email_template_name='registration/email_change_email.txt'):
    try:
        url = ec.get_url()
        url = request.build_absolute_uri(url)
        t = loader.get_template(email_template_name)
        c = {'url': url, 'site_name': SITENAME}
        from_email = settings.SERVER_EMAIL
        send_mail(_(EMAIL_CHANGE_EMAIL_SUBJECT),
                  t.render(Context(c)), from_email, [ec.new_email_address])
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise ChangeEmailError()
    else:
        msg = 'Sent change email for %s' % ec.user.email
        logger.log(LOGGING_LEVEL, msg)


def activate(
    user,
    email_template_name='im/welcome_email.txt',
    helpdesk_email_template_name='im/helpdesk_notification.txt',
    verify_email=False):
    """
    Activates the specific user and sends email.

    Raises SendGreetingError, ValidationError
    """
    user.is_active = True
    user.email_verified = True
    if not user.activation_sent:
        user.activation_sent = datetime.now()
    user.save()
    send_helpdesk_notification(user, helpdesk_email_template_name)
    send_greeting(user, email_template_name)

def invite(inviter, email, realname):
    inv = Invitation(inviter=inviter, username=email, realname=realname)
    inv.save()
    send_invitation(inv)
    inviter.invitations = max(0, self.invitations - 1)
    inviter.save()

def switch_account_to_shibboleth(user, local_user,
                                 greeting_template_name='im/welcome_email.txt'):
    try:
        provider = user.provider
    except AttributeError:
        return
    else:
        if not provider == 'shibboleth':
            return
        user.delete()
        local_user.provider = 'shibboleth'
        local_user.third_party_identifier = user.third_party_identifier
        local_user.save()
        send_greeting(local_user, greeting_template_name)
        return local_user


class SendMailError(Exception):
    pass


class SendAdminNotificationError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.ADMIN_NOTIFICATION_SEND_ERR)
        super(SendAdminNotificationError, self).__init__()


class SendVerificationError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.VERIFICATION_SEND_ERR)
        super(SendVerificationError, self).__init__()


class SendInvitationError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.INVITATION_SEND_ERR)
        super(SendInvitationError, self).__init__()


class SendGreetingError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.GREETING_SEND_ERR)
        super(SendGreetingError, self).__init__()


class SendFeedbackError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.FEEDBACK_SEND_ERR)
        super(SendFeedbackError, self).__init__()


class ChangeEmailError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.CHANGE_EMAIL_SEND_ERR)
        super(ChangeEmailError, self).__init__()


class SendNotificationError(SendMailError):
    def __init__(self):
        self.message = _(astakos_messages.NOTIFICATION_SEND_ERR)
        super(SendNotificationError, self).__init__()


### PROJECT VIEWS ###

AUTO_ACCEPT_POLICY = 1
MODERATED_POLICY   = 2
CLOSED_POLICY      = 3

POLICIES = [ AUTO_ACCEPT_POLICY, MODERATED_POLICY, CLOSED_POLICY ]

def get_project_by_application_id(project_application_id):
    try:
        return Project.objects.get(application__id=project_application_id)
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) % project_application_id)

def get_project_id_of_application_id(project_application_id):
    try:
        return Project.objects.get(application__id=project_application_id).id
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) % project_application_id)

def get_project_by_id(project_id):
    try:
        return Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id)

def get_project_for_update(project_id):
    try:
        return Project.objects.select_for_update().get(id=project_id)
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id)

def get_user_by_id(user_id):
    try:
        return AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        raise IOError(_(astakos_messages.UNKNOWN_USER_ID) % user_id)

def create_membership(project, user):
    if isinstance(project, int):
        project = get_project_by_id(project)
    if isinstance(user, int):
        user = get_user_by_id(user)
    m = ProjectMembership(
        project=project,
        person=user,
        request_date=datetime.now())
    try:
        m.save()
    except IntegrityError, e:
        raise IOError(_(astakos_messages.MEMBERSHIP_REQUEST_EXISTS))
    else:
        return m

def get_membership_for_update(project, user):
    if isinstance(project, int):
        project = get_project_by_id(project)
    if isinstance(user, int):
        user = get_user_by_id(user)
    try:
        return ProjectMembership.objects.select_for_update().get(
            project=project,
            person=user)
    except ProjectMembership.DoesNotExist:
        raise IOError(_(astakos_messages.NOT_MEMBERSHIP_REQUEST))

def accept_membership(project_application_id, user, request_user=None):
    """
        Raises:
            django.core.exceptions.PermissionDenied
            IOError
    """
    project_id = get_project_id_of_application_id(project_application_id)
    return do_accept_membership(project_id, user, request_user)

def do_accept_membership_checks(project, request_user):
    if request_user and \
        (not project.application.owner == request_user and \
            not request_user.is_superuser):
        raise PermissionDenied(_(astakos_messages.NOT_ALLOWED))
    if not project.is_alive:
        raise PermissionDenied(
            _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_JOIN_POLICY_CLOSED))

    if project.violates_members_limit(adding=1):
        raise PermissionDenied(_(astakos_messages.MEMBER_NUMBER_LIMIT_REACHED))

def do_accept_membership(
        project_id, user, request_user=None, bypass_checks=False):
    project = get_project_for_update(project_id)

    if not bypass_checks:
        do_accept_membership_checks(project, request_user)

    membership = get_membership_for_update(project, user)
    membership.accept()
    trigger_sync()

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [membership.person.email],
            _(PROJECT_MEMBERSHIP_CHANGE_SUBJECT) % project.__dict__,
            template='im/projects/project_membership_change_notification.txt',
            dictionary={'object':project.application, 'action':'accepted'})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)
    return membership

def reject_membership(project_application_id, user, request_user=None):
    """
        Raises:
            django.core.exceptions.PermissionDenied
            IOError
    """
    project_id = get_project_id_of_application_id(project_application_id)
    return do_reject_membership(project_id, user, request_user)

def do_reject_membership_checks(project, request_user):
    if request_user and \
        (not project.application.owner == request_user and \
            not request_user.is_superuser):
        raise PermissionDenied(_(astakos_messages.NOT_ALLOWED))
    if not project.is_alive:
        raise PermissionDenied(
            _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)

def do_reject_membership(
        project_id, user, request_user=None, bypass_checks=False):
    project = get_project_for_update(project_id)

    if not bypass_checks:
        do_reject_membership_checks(project, request_user)

    membership = get_membership_for_update(project, user)
    membership.reject()

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [membership.person.email],
            _(PROJECT_MEMBERSHIP_CHANGE_SUBJECT) % project.__dict__,
            template='im/projects/project_membership_change_notification.txt',
            dictionary={'object':project.application, 'action':'rejected'})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)
    return membership

def remove_membership(project_application_id, user, request_user=None):
    """
        Raises:
            django.core.exceptions.PermissionDenied
            IOError
    """
    project_id = get_project_id_of_application_id(project_application_id)
    return do_remove_membership(project_id, user, request_user)

def do_remove_membership_checks(project, membership):
    if request_user and \
        (not project.application.owner == request_user and \
            not request_user.is_superuser):
        raise PermissionDenied(_(astakos_messages.NOT_ALLOWED))
    if not project.is_alive:
        raise PermissionDenied(
            _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)

def do_remove_membership(
        project_id, user, request_user=None, bypass_checks=False):
    project = get_project_for_update(project_id)

    if not bypass_checks:
        do_remove_membership_checks(project, request_user)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED))

    membership = get_membership_for_update(project, user)
    membership.remove()
    trigger_sync()

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [membership.person.email],
            _(PROJECT_MEMBERSHIP_CHANGE_SUBJECT) % project.__dict__,
            template='im/projects/project_membership_change_notification.txt',
            dictionary={'object':project.application, 'action':'removed'})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)
    return membership

def enroll_member(project_application_id, user, request_user=None):
    project_id = get_project_id_of_application_id(project_application_id)
    return do_enroll_member(project_id, user, request_user)

def do_enroll_member(project_id, user, request_user=None):
    membership = create_membership(project_id, user)
    return do_accept_membership(
        project_id, user, request_user, bypass_checks=True)

def leave_project(project_application_id, user_id):
    """
        Raises:
            django.core.exceptions.PermissionDenied
            IOError
    """
    project_id = get_project_id_of_application_id(project_application_id)
    return do_leave_project(project_id, user_id)

def do_leave_project_checks(project):
    if not project.is_alive:
        m = _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__
        raise PermissionDenied(m)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED))

def do_leave_project(project_id, user_id, bypass_checks=False):
    project = get_project_for_update(project_id)

    if not bypass_checks:
        do_leave_project_checks(project)

    membership = get_membership_for_update(project, user_id)

    leave_policy = project.application.member_leave_policy
    if leave_policy == AUTO_ACCEPT_POLICY:
        membership.remove()
        trigger_sync()
    else:
        membership.leave_request_date = datetime.now()
        membership.save()
    return membership

def join_project(project_application_id, user_id):
    """
        Raises:
            django.core.exceptions.PermissionDenied
            IOError
    """
    project_id = get_project_id_of_application_id(project_application_id)
    return do_join_project(project_id, user_id)

def do_join_project_checks(project):
    if not project.is_alive:
        m = _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__
        raise PermissionDenied(m)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_JOIN_POLICY_CLOSED))

def do_join_project(project_id, user_id, bypass_checks=False):
    project = get_project_for_update(project_id)

    if not bypass_checks:
        do_join_project_checks(project)

    membership = create_membership(project, user_id)

    join_policy = project.application.member_join_policy
    if (join_policy == AUTO_ACCEPT_POLICY and
        not project.violates_members_limit(adding=1)):
        membership.accept()
        trigger_sync()
    return membership

def submit_application(
        application, resource_policies, applicant, comments,
        precursor_application=None):

    application.submit(
        resource_policies, applicant, comments, precursor_application)

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [i[1] for i in settings.ADMINS],
            _(PROJECT_CREATION_SUBJECT) % application.__dict__,
            template='im/projects/project_creation_notification.txt',
            dictionary={'object':application})
        notification.send()
    except NotificationError, e:
        logger.error(e)
    return application

def update_application(app_id, **kw):
    app = ProjectApplication.objects.get(id=app_id)
    app.id = None
    app.state = app.PENDING
    app.precursor_application_id = app_id
    app.issue_date = datetime.now()

    resource_policies = kw.pop('resource_policies', None)
    for k, v in kw.iteritems():
        setattr(app, k, v)
    app.save()
    app.resource_policies = resource_policies
    return app.id

def approve_application(app):

    app_id = app if isinstance(app, int) else app.id

    try:
        objects = ProjectApplication.objects.select_for_update()
        application = objects.get(id=app_id)
    except ProjectApplication.DoesNotExist:
        raise PermissionDenied()

    application.approve()
    trigger_sync()

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [application.owner.email],
            _(PROJECT_APPROVED_SUBJECT) % application.__dict__,
            template='im/projects/project_approval_notification.txt',
            dictionary={'object':application})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def terminate(project_id):
    project = get_project_for_update(project_id)

    if not project.is_alive:
        m = _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__
        raise PermissionDenied(m)

    project.terminate()
    trigger_sync()

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [project.application.owner.email],
            _(PROJECT_TERMINATION_SUBJECT) % project.__dict__,
            template='im/projects/project_termination_notification.txt',
            dictionary={'object':project.application}
        ).send()
    except NotificationError, e:
        logger.error(e.message)

def suspend(project_id):
    project = get_project_by_id(project_id)
    project.last_approval_date = None
    project.save()
    trigger_sync()

    try:
        notification = build_notification(
            settings.SERVER_EMAIL,
            [project.application.owner.email],
            _(PROJECT_SUSPENSION_SUBJECT) % project.__dict__,
            template='im/projects/project_suspension_notification.txt',
            dictionary={'object':project.application}
        ).send()
    except NotificationError, e:
        logger.error(e.message)

# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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
from django.core.mail import send_mail, get_connection
from django.core.urlresolvers import reverse
from django.template import Context, loader
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout)
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import Http404

from urllib import quote
from urlparse import urljoin
from smtplib import SMTPException
from datetime import datetime
from functools import wraps

import astakos.im.settings as astakos_settings
from astakos.im.settings import (
    CONTACT_EMAIL, SITENAME, BASEURL, LOGGING_LEVEL,
    VERIFICATION_EMAIL_SUBJECT, ACCOUNT_CREATION_SUBJECT,
    GROUP_CREATION_SUBJECT, HELPDESK_NOTIFICATION_EMAIL_SUBJECT,
    INVITATION_EMAIL_SUBJECT, GREETING_EMAIL_SUBJECT, FEEDBACK_EMAIL_SUBJECT,
    EMAIL_CHANGE_EMAIL_SUBJECT,
    PROJECT_CREATION_SUBJECT, PROJECT_APPROVED_SUBJECT,
    PROJECT_TERMINATION_SUBJECT, PROJECT_SUSPENSION_SUBJECT,
    PROJECT_MEMBERSHIP_CHANGE_SUBJECT,
    PROJECT_MEMBER_JOIN_POLICIES, PROJECT_MEMBER_LEAVE_POLICIES, HELPDESK,
    ADMINS, MANAGERS)
from astakos.im.notifications import build_notification, NotificationError
from astakos.im.models import (
    AstakosUser, Invitation, ProjectMembership, ProjectApplication, Project,
    UserSetting,
    get_resource_names, new_chain)
from astakos.im.quotas import qh_sync_user, qh_sync_users
from astakos.im.project_notif import (
    membership_change_notify, membership_enroll_notify,
    membership_request_notify, membership_leave_request_notify,
    application_submit_notify, application_approve_notify,
    application_deny_notify,
    project_termination_notify, project_suspension_notify)

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
    logger.info('%s logged out.', user.log_display)


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
                               'support': CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    try:
        send_mail(_(VERIFICATION_EMAIL_SUBJECT), message, sender, [user.email],
                  connection=get_connection())

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
    Send notification email to settings.HELPDESK + settings.MANAGERS.

    Raises SendNotificationError
    """
    dictionary = dictionary or {}
    message = render_to_string(template_name, dictionary)
    sender = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in HELPDESK + MANAGERS]
    try:
        send_mail(subject, message, sender, recipient_list,
                  connection=get_connection())
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendNotificationError()
    else:
        user = dictionary.get('user')
        msg = 'Sent admin notification for user %s' % user.log_display
        logger.log(LOGGING_LEVEL, msg)


def send_account_creation_notification(template_name, dictionary=None):
    user = dictionary.get('user')
    subject = _(ACCOUNT_CREATION_SUBJECT) % {'user': user.email}
    return _send_admin_notification(template_name, dictionary, subject=subject)


def send_helpdesk_notification(user, template_name='im/helpdesk_notification.txt'):
    """
    Send email to settings.HELPDESK list to notify for a new user activation.

    Raises SendNotificationError
    """
    message = render_to_string(
        template_name,
        {'user': user}
    )
    sender = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in HELPDESK + MANAGERS]
    try:
        send_mail(_(HELPDESK_NOTIFICATION_EMAIL_SUBJECT) % {'user': user.email},
                  message, sender, recipient_list, connection=get_connection())
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
                               'support': CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    try:
        send_mail(subject, message, sender, [invitation.username],
                  connection=get_connection())
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendInvitationError()
    else:
        msg = 'Sent invitation %s' % invitation
        logger.log(LOGGING_LEVEL, msg)
        inviter_invitations = invitation.inviter.invitations
        invitation.inviter.invitations = max(0, inviter_invitations - 1)
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
                               'support': CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    try:
        send_mail(subject, message, sender, [user.email],
                  connection=get_connection())
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendGreetingError()
    else:
        msg = 'Sent greeting %s' % user.log_display
        logger.log(LOGGING_LEVEL, msg)


def send_feedback(msg, data, user, email_template_name='im/feedback_mail.txt'):
    subject = _(FEEDBACK_EMAIL_SUBJECT)
    from_email = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in HELPDESK]
    content = render_to_string(email_template_name, {
        'message': msg,
        'data': data,
        'user': user})
    try:
        send_mail(subject, content, from_email, recipient_list,
                  connection=get_connection())
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise SendFeedbackError()
    else:
        msg = 'Sent feedback from %s' % user.log_display
        logger.log(LOGGING_LEVEL, msg)


def send_change_email(
    ec, request, email_template_name='registration/email_change_email.txt'):
    try:
        url = ec.get_url()
        url = request.build_absolute_uri(url)
        t = loader.get_template(email_template_name)
        c = {'url': url, 'site_name': SITENAME,
             'support': CONTACT_EMAIL, 'ec': ec}
        from_email = settings.SERVER_EMAIL
        send_mail(_(EMAIL_CHANGE_EMAIL_SUBJECT), t.render(Context(c)),
                  from_email, [ec.new_email_address],
                  connection=get_connection())
    except (SMTPException, socket.error) as e:
        logger.exception(e)
        raise ChangeEmailError()
    else:
        msg = 'Sent change email for %s' % ec.user.log_display
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
    qh_sync_user(user.id)
    send_helpdesk_notification(user, helpdesk_email_template_name)
    send_greeting(user, email_template_name)

def deactivate(user):
    user.is_active = False
    user.save()

def invite(inviter, email, realname):
    inv = Invitation(inviter=inviter, username=email, realname=realname)
    inv.save()
    send_invitation(inv)
    inviter.invitations = max(0, inviter.invitations - 1)
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


def get_quota(users):
    pass


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

def get_related_project_id(application_id):
    try:
        app = ProjectApplication.objects.get(id=application_id)
        chain = app.chain
        project = Project.objects.get(id=chain)
        return chain
    except:
        return None

def get_chain_of_application_id(application_id):
    try:
        app = ProjectApplication.objects.get(id=application_id)
        chain = app.chain
        return chain.chain
    except:
        return None

def get_project_by_id(project_id):
    try:
        return Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id)

def get_project_by_name(name):
    try:
        return Project.objects.get(name=name)
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_ID) % name)


def get_project_for_update(project_id):
    try:
        return Project.objects.get_for_update(id=project_id)
    except Project.DoesNotExist:
        raise IOError(
            _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id)

def get_application_for_update(application_id):
    try:
        return ProjectApplication.objects.get_for_update(id=application_id)
    except ProjectApplication.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) % application_id
        raise IOError(m)

def get_user_by_id(user_id):
    try:
        return AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        raise IOError(_(astakos_messages.UNKNOWN_USER_ID) % user_id)

def get_user_by_uuid(uuid):
    try:
        return AstakosUser.objects.get(uuid=uuid)
    except AstakosUser.DoesNotExist:
        raise IOError(_(astakos_messages.UNKNOWN_USER_ID) % uuid)

def create_membership(project, user):
    if isinstance(user, (int, long)):
        user = get_user_by_id(user)

    if not user.is_active:
        m = _(astakos_messages.ACCOUNT_NOT_ACTIVE)
        raise PermissionDenied(m)

    m, created = ProjectMembership.objects.get_or_create(
        project=project,
        person=user)

    if created:
        return m
    else:
        msg = _(astakos_messages.MEMBERSHIP_REQUEST_EXISTS)
        raise PermissionDenied(msg)


def get_membership_for_update(project, user):
    if isinstance(user, (int, long)):
        user = get_user_by_id(user)
    try:
        objs = ProjectMembership.objects
        m = objs.get_for_update(project=project, person=user)
        return m
    except ProjectMembership.DoesNotExist:
        raise IOError(_(astakos_messages.NOT_MEMBERSHIP_REQUEST))

def checkAllowed(entity, request_user):
    if isinstance(entity, Project):
        application = entity.application
    elif isinstance(entity, ProjectApplication):
        application = entity
    else:
        m = "%s not a Project nor a ProjectApplication" % (entity,)
        raise ValueError(m)

    if request_user and \
        (not application.owner == request_user and \
            not request_user.is_superuser):
        raise PermissionDenied(_(astakos_messages.NOT_ALLOWED))

def checkAlive(project):
    if not project.is_alive:
        raise PermissionDenied(
            _(astakos_messages.NOT_ALIVE_PROJECT) % project.__dict__)

def accept_membership_checks(project, request_user):
    checkAllowed(project, request_user)
    checkAlive(project)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_JOIN_POLICY_CLOSED))

    if project.violates_members_limit(adding=1):
        raise PermissionDenied(_(astakos_messages.MEMBER_NUMBER_LIMIT_REACHED))

def accept_membership(project_id, user, request_user=None):
    project = get_project_for_update(project_id)
    accept_membership_checks(project, request_user)

    membership = get_membership_for_update(project, user)
    if not membership.can_accept():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    membership.accept()
    qh_sync_user(user)
    logger.info("User %s has been accepted in %s." %
                (membership.person.log_display, project))

    membership_change_notify(project, membership.person, 'accepted')

    return membership

def reject_membership_checks(project, request_user):
    checkAllowed(project, request_user)
    checkAlive(project)

def reject_membership(project_id, user, request_user=None):
    project = get_project_for_update(project_id)
    reject_membership_checks(project, request_user)
    membership = get_membership_for_update(project, user)
    if not membership.can_reject():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    membership.reject()
    logger.info("Request of user %s for %s has been rejected." %
                (membership.person.log_display, project))

    membership_change_notify(project, membership.person, 'rejected')

    return membership

def cancel_membership_checks(project):
    checkAlive(project)

def cancel_membership(project_id, user_id):
    project = get_project_for_update(project_id)
    cancel_membership_checks(project)
    membership = get_membership_for_update(project, user_id)
    if not membership.can_cancel():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    membership.cancel()
    logger.info("Request of user %s for %s has been cancelled." %
                (membership.person.log_display, project))

def remove_membership_checks(project, request_user=None):
    checkAllowed(project, request_user)
    checkAlive(project)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED))

def remove_membership(project_id, user, request_user=None):
    project = get_project_for_update(project_id)
    remove_membership_checks(project, request_user)
    membership = get_membership_for_update(project, user)
    if not membership.can_remove():
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise PermissionDenied(m)

    membership.remove()
    qh_sync_user(user)
    logger.info("User %s has been removed from %s." %
                (membership.person.log_display, project))

    membership_change_notify(project, membership.person, 'removed')

    return membership

def enroll_member(project_id, user, request_user=None):
    project = get_project_for_update(project_id)
    accept_membership_checks(project, request_user)

    membership, created = ProjectMembership.objects.get_or_create(
        project=project,
        person=user)

    if not membership.can_accept():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    membership.accept()
    qh_sync_user(user.id)
    logger.info("User %s has been enrolled in %s." %
                (membership.person.log_display, project))

    membership_enroll_notify(project, membership.person)

    return membership

def leave_project_checks(project):
    checkAlive(project)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED))

def can_leave_request(project, user):
    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        return False
    m = user.get_membership(project)
    if m is None:
        return False
    if m.state != ProjectMembership.ACCEPTED:
        return False
    return True

def leave_project(project_id, user_id):
    project = get_project_for_update(project_id)
    leave_project_checks(project)
    membership = get_membership_for_update(project, user_id)
    if not membership.can_leave():
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise PermissionDenied(m)

    auto_accepted = False
    leave_policy = project.application.member_leave_policy
    if leave_policy == AUTO_ACCEPT_POLICY:
        membership.remove()
        qh_sync_user(user_id)
        logger.info("User %s has left %s." %
                    (membership.person.log_display, project))
        auto_accepted = True
    else:
        membership.leave_request()
        logger.info("User %s requested to leave %s." %
                    (membership.person.log_display, project))
        membership_leave_request_notify(project, membership.person)
    return auto_accepted

def join_project_checks(project):
    checkAlive(project)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        raise PermissionDenied(_(astakos_messages.MEMBER_JOIN_POLICY_CLOSED))

def can_join_request(project, user):
    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        return False
    m = user.get_membership(project)
    if m:
        return False
    return True

def join_project(project_id, user_id):
    project = get_project_for_update(project_id)
    join_project_checks(project)
    membership = create_membership(project, user_id)

    auto_accepted = False
    join_policy = project.application.member_join_policy
    if (join_policy == AUTO_ACCEPT_POLICY and
        not project.violates_members_limit(adding=1)):
        membership.accept()
        qh_sync_user(user_id)
        logger.info("User %s joined %s." %
                    (membership.person.log_display, project))
        auto_accepted = True
    else:
        membership_request_notify(project, membership.person)
        logger.info("User %s requested to join %s." %
                    (membership.person.log_display, project))

    return auto_accepted

def submit_application(kw, request_user=None):

    kw['applicant'] = request_user
    resource_policies = kw.pop('resource_policies', None)

    precursor = None
    precursor_id = kw.get('precursor_application', None)
    if precursor_id is not None:
        objs = ProjectApplication.objects
        precursor = objs.get_for_update(id=precursor_id)
        kw['precursor_application'] = precursor

        if (request_user and
            (not precursor.owner == request_user and
             not request_user.is_superuser
             and not request_user.is_project_admin())):
            m = _(astakos_messages.NOT_ALLOWED)
            raise PermissionDenied(m)

    owner = kw['owner']
    reached, limit = reached_pending_application_limit(owner.id, precursor)
    if not request_user.is_project_admin() and reached:
        m = _(astakos_messages.REACHED_PENDING_APPLICATION_LIMIT) % limit
        raise PermissionDenied(m)

    application = ProjectApplication(**kw)

    if precursor is None:
        application.chain = new_chain()
    else:
        chain = precursor.chain
        application.chain = chain
        objs = ProjectApplication.objects
        q = objs.filter(chain=chain, state=ProjectApplication.PENDING)
        pending = q.select_for_update()
        for app in pending:
            app.state = ProjectApplication.REPLACED
            app.save()

    application.save()
    application.resource_policies = resource_policies
    logger.info("User %s submitted %s." %
                (request_user.log_display, application.log_display))
    application_submit_notify(application)
    return application

def cancel_application(application_id, request_user=None):
    application = get_application_for_update(application_id)
    checkAllowed(application, request_user)

    if not application.can_cancel():
        m = _(astakos_messages.APPLICATION_CANNOT_CANCEL % (
                application.id, application.state_display()))
        raise PermissionDenied(m)

    application.cancel()
    logger.info("%s has been cancelled." % (application.log_display))

def dismiss_application(application_id, request_user=None):
    application = get_application_for_update(application_id)
    checkAllowed(application, request_user)

    if not application.can_dismiss():
        m = _(astakos_messages.APPLICATION_CANNOT_DISMISS % (
                application.id, application.state_display()))
        raise PermissionDenied(m)

    application.dismiss()
    logger.info("%s has been dismissed." % (application.log_display))

def deny_application(application_id, reason=None):
    application = get_application_for_update(application_id)

    if not application.can_deny():
        m = _(astakos_messages.APPLICATION_CANNOT_DENY % (
                application.id, application.state_display()))
        raise PermissionDenied(m)

    if reason is None:
        reason = ""
    application.deny(reason)
    logger.info("%s has been denied with reason \"%s\"." %
                (application.log_display, reason))
    application_deny_notify(application)

def approve_application(app_id):

    try:
        objects = ProjectApplication.objects
        application = objects.get_for_update(id=app_id)
    except ProjectApplication.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID % (app_id,))
        raise PermissionDenied(m)

    if not application.can_approve():
        m = _(astakos_messages.APPLICATION_CANNOT_APPROVE % (
                application.id, application.state_display()))
        raise PermissionDenied(m)

    project = application.approve()
    qh_sync_projects([project])
    logger.info("%s has been approved." % (application.log_display))
    application_approve_notify(application)

def check_expiration(execute=False):
    objects = Project.objects
    expired = objects.expired_projects()
    if execute:
        for project in expired:
            terminate(project.id)

    return [project.expiration_info() for project in expired]

def terminate(project_id):
    project = get_project_for_update(project_id)
    checkAlive(project)

    project.terminate()
    qh_sync_projects([project])
    logger.info("%s has been terminated." % (project))

    project_termination_notify(project)

def suspend(project_id):
    project = get_project_by_id(project_id)
    checkAlive(project)

    project.suspend()
    qh_sync_projects([project])
    logger.info("%s has been suspended." % (project))

    project_suspension_notify(project)

def resume(project_id):
    project = get_project_for_update(project_id)

    if not project.is_suspended:
        m = _(astakos_messages.NOT_SUSPENDED_PROJECT) % project.__dict__
        raise PermissionDenied(m)

    project.resume()
    qh_sync_projects([project])
    logger.info("%s has been unsuspended." % (project))

def get_by_chain_or_404(chain_id):
    try:
        project = Project.objects.get(id=chain_id)
        application = project.application
        return project, application
    except:
        application = ProjectApplication.objects.latest_of_chain(chain_id)
        if application is None:
            raise Http404
        else:
            return None, application


def get_user_setting(user_id, key):
    try:
        setting = UserSetting.objects.get(
            user=user_id, setting=key)
        return setting.value
    except UserSetting.DoesNotExist:
        return getattr(astakos_settings, key)


def set_user_setting(user_id, key, value):
    try:
        setting = UserSetting.objects.get_for_update(
            user=user_id, setting=key)
    except UserSetting.DoesNotExist:
        setting = UserSetting(user_id=user_id, setting=key)
    setting.value = value
    setting.save()


def unset_user_setting(user_id, key):
    UserSetting.objects.filter(user=user_id, setting=key).delete()


PENDING_APPLICATION_LIMIT_SETTING = 'PENDING_APPLICATION_LIMIT'

def get_pending_application_limit(user_id):
    key = PENDING_APPLICATION_LIMIT_SETTING
    return get_user_setting(user_id, key)


def set_pending_application_limit(user_id, value):
    key = PENDING_APPLICATION_LIMIT_SETTING
    return set_user_setting(user_id, key, value)


def unset_pending_application_limit(user_id):
    key = PENDING_APPLICATION_LIMIT_SETTING
    return unset_user_setting(user_id, key)


def _reached_pending_application_limit(user_id):
    limit = get_pending_application_limit(user_id)

    PENDING = ProjectApplication.PENDING
    pending = ProjectApplication.objects.filter(
        owner__id=user_id, state=PENDING).count()

    return pending >= limit, limit


def reached_pending_application_limit(user_id, precursor=None):
    reached, limit = _reached_pending_application_limit(user_id)

    if precursor is None:
        return reached, limit

    chain = precursor.chain
    objs = ProjectApplication.objects
    q = objs.filter(chain=chain, state=ProjectApplication.PENDING)
    has_pending = q.exists()

    if not has_pending:
        return reached, limit

    return False, limit


def qh_sync_projects(projects):

    memberships = ProjectMembership.objects.filter(project__in=projects)
    user_ids = set(m.person_id for m in memberships)

    qh_sync_users(user_ids)

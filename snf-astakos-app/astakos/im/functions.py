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
from datetime import datetime

from django.utils.translation import ugettext as _
from django.core.mail import send_mail, get_connection
from django.core.urlresolvers import reverse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.db.models import Q

from synnefo_branding.utils import render_to_string

from synnefo.lib import join_urls
from astakos.im.models import AstakosUser, Invitation, ProjectMembership, \
    ProjectApplication, Project, new_chain, Resource, ProjectLock
from astakos.im.quotas import qh_sync_user, get_pending_app_quota, \
    register_pending_apps, qh_sync_project, qh_sync_locked_users, \
    get_users_for_update, members_to_sync
from astakos.im.project_notif import membership_change_notify, \
    membership_enroll_notify, membership_request_notify, \
    membership_leave_request_notify, application_submit_notify, \
    application_approve_notify, application_deny_notify, \
    project_termination_notify, project_suspension_notify, \
    project_unsuspension_notify, project_reinstatement_notify
from astakos.im import settings

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
    """
    url = join_urls(settings.BASE_HOST,
                    user.get_activation_url(nxt=reverse('index')))
    message = render_to_string(template_name, {
                               'user': user,
                               'url': url,
                               'baseurl': settings.BASE_URL,
                               'site_name': settings.SITENAME,
                               'support': settings.CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    send_mail(_(astakos_messages.VERIFICATION_EMAIL_SUBJECT), message, sender,
              [user.email],
              connection=get_connection())
    logger.info("Sent user verirfication email: %s", user.log_display)


def _send_admin_notification(template_name,
                             context=None,
                             user=None,
                             msg="",
                             subject='alpha2 testing notification',):
    """
    Send notification email to settings.HELPDESK + settings.MANAGERS +
    settings.ADMINS.
    """
    if context is None:
        context = {}
    if not 'user' in context:
        context['user'] = user

    message = render_to_string(template_name, context)
    sender = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in settings.HELPDESK +
                      settings.MANAGERS + settings.ADMINS]
    send_mail(subject, message, sender, recipient_list,
              connection=get_connection())
    if user:
        msg = 'Sent admin notification (%s) for user %s' % (msg,
                                                            user.log_display)
    else:
        msg = 'Sent admin notification (%s)' % msg

    logger.log(settings.LOGGING_LEVEL, msg)


def send_account_pending_moderation_notification(
        user,
        template_name='im/account_pending_moderation_notification.txt'):
    """
    Notify admins that a new user has verified his email address and moderation
    step is required to activate his account.
    """
    subject = (_(astakos_messages.ACCOUNT_CREATION_SUBJECT) %
               {'user': user.email})
    return _send_admin_notification(template_name, {}, subject=subject,
                                    user=user, msg="account creation")


def send_account_activated_notification(
        user,
        template_name='im/account_activated_notification.txt'):
    """
    Send email to settings.HELPDESK + settings.MANAGERES + settings.ADMINS
    lists to notify that a new account has been accepted and activated.
    """
    message = render_to_string(
        template_name,
        {'user': user}
    )
    sender = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in settings.HELPDESK +
                      settings.MANAGERS + settings.ADMINS]
    send_mail(_(astakos_messages.HELPDESK_NOTIFICATION_EMAIL_SUBJECT) %
              {'user': user.email},
              message, sender, recipient_list, connection=get_connection())
    msg = 'Sent helpdesk admin notification for %s' % user.email
    logger.log(settings.LOGGING_LEVEL, msg)


def send_invitation(invitation, template_name='im/invitation.txt'):
    """
    Send invitation email.
    """
    subject = _(astakos_messages.INVITATION_EMAIL_SUBJECT)
    url = '%s?code=%d' % (join_urls(settings.BASE_HOST,
                                    reverse('index')), invitation.code)
    message = render_to_string(template_name, {
                               'invitation': invitation,
                               'url': url,
                               'baseurl': settings.BASE_URL,
                               'site_name': settings.SITENAME,
                               'support': settings.CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    send_mail(subject, message, sender, [invitation.username],
              connection=get_connection())
    msg = 'Sent invitation %s' % invitation
    logger.log(settings.LOGGING_LEVEL, msg)
    inviter_invitations = invitation.inviter.invitations
    invitation.inviter.invitations = max(0, inviter_invitations - 1)
    invitation.inviter.save()


def send_greeting(user, email_template_name='im/welcome_email.txt'):
    """
    Send welcome email to an accepted/activated user.

    Raises SMTPException, socket.error
    """
    subject = _(astakos_messages.GREETING_EMAIL_SUBJECT)
    message = render_to_string(email_template_name, {
                               'user': user,
                               'url': join_urls(settings.BASE_HOST,
                                                reverse('index')),
                               'baseurl': settings.BASE_URL,
                               'site_name': settings.SITENAME,
                               'support': settings.CONTACT_EMAIL})
    sender = settings.SERVER_EMAIL
    send_mail(subject, message, sender, [user.email],
              connection=get_connection())
    msg = 'Sent greeting %s' % user.log_display
    logger.log(settings.LOGGING_LEVEL, msg)


def send_feedback(msg, data, user, email_template_name='im/feedback_mail.txt'):
    subject = _(astakos_messages.FEEDBACK_EMAIL_SUBJECT)
    from_email = settings.SERVER_EMAIL
    recipient_list = [e[1] for e in settings.HELPDESK]
    content = render_to_string(email_template_name, {
        'message': msg,
        'data': data,
        'user': user})
    send_mail(subject, content, from_email, recipient_list,
              connection=get_connection())
    msg = 'Sent feedback from %s' % user.log_display
    logger.log(settings.LOGGING_LEVEL, msg)


def send_change_email(
    ec, request, email_template_name='registration/email_change_email.txt'
):
    url = ec.get_url()
    url = request.build_absolute_uri(url)
    c = {'url': url, 'site_name': settings.SITENAME,
         'support': settings.CONTACT_EMAIL,
         'ec': ec}
    message = render_to_string(email_template_name, c)
    from_email = settings.SERVER_EMAIL
    send_mail(_(astakos_messages.EMAIL_CHANGE_EMAIL_SUBJECT), message,
              from_email,
              [ec.new_email_address], connection=get_connection())
    msg = 'Sent change email for %s' % ec.user.log_display
    logger.log(settings.LOGGING_LEVEL, msg)


def invite(inviter, email, realname):
    inv = Invitation(inviter=inviter, username=email, realname=realname)
    inv.save()
    send_invitation(inv)
    inviter.invitations = max(0, inviter.invitations - 1)
    inviter.save()


### PROJECT FUNCTIONS ###


class ProjectError(Exception):
    pass


class ProjectNotFound(ProjectError):
    pass


class ProjectForbidden(ProjectError):
    pass


class ProjectBadRequest(ProjectError):
    pass


class ProjectConflict(ProjectError):
    pass

AUTO_ACCEPT_POLICY = 1
MODERATED_POLICY = 2
CLOSED_POLICY = 3

POLICIES = [AUTO_ACCEPT_POLICY, MODERATED_POLICY, CLOSED_POLICY]


def get_related_project_id(application_id):
    try:
        app = ProjectApplication.objects.get(id=application_id)
        return app.chain_id
    except ProjectApplication.DoesNotExist:
        return None


def get_project_by_id(project_id):
    try:
        return Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id
        raise ProjectNotFound(m)


def get_project_for_update(project_id):
    try:
        return Project.objects.get_for_update(id=project_id)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id
        raise ProjectNotFound(m)


def get_project_of_application_for_update(app_id):
    app = get_application(app_id)
    return get_project_for_update(app.chain_id)


def get_project_lock():
    ProjectLock.objects.get_for_update(pk=1)


def get_application(application_id):
    try:
        return ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) % application_id
        raise ProjectNotFound(m)


def get_project_of_membership_for_update(memb_id):
    m = get_membership_by_id(memb_id)
    return get_project_for_update(m.project_id)


def get_user_by_id(user_id):
    try:
        return AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_USER_ID) % user_id
        raise ProjectNotFound(m)


def get_user_by_uuid(uuid):
    try:
        return AstakosUser.objects.get(uuid=uuid)
    except AstakosUser.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_USER_ID) % uuid
        raise ProjectNotFound(m)


def get_membership(project_id, user_id):
    try:
        objs = ProjectMembership.objects.select_related('project', 'person')
        return objs.get(project__id=project_id, person__id=user_id)
    except ProjectMembership.DoesNotExist:
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise ProjectNotFound(m)


def get_membership_by_id(memb_id):
    try:
        objs = ProjectMembership.objects.select_related('project', 'person')
        return objs.get(id=memb_id)
    except ProjectMembership.DoesNotExist:
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise ProjectNotFound(m)


ALLOWED_CHECKS = [
    (lambda u, a: not u or u.is_project_admin()),
    (lambda u, a: a.owner == u),
    (lambda u, a: a.applicant == u),
    (lambda u, a: a.chain.overall_state() == Project.O_ACTIVE
     or bool(a.chain.projectmembership_set.any_accepted().filter(person=u))),
]

ADMIN_LEVEL = 0
OWNER_LEVEL = 1
APPLICANT_LEVEL = 2
ANY_LEVEL = 3


def _check_yield(b, silent=False):
    if b:
        return True

    if silent:
        return False

    m = _(astakos_messages.NOT_ALLOWED)
    raise ProjectForbidden(m)


def membership_check_allowed(membership, request_user,
                             level=OWNER_LEVEL, silent=False):
    r = project_check_allowed(
        membership.project, request_user, level, silent=True)

    return _check_yield(r or membership.person == request_user, silent)


def project_check_allowed(project, request_user,
                          level=OWNER_LEVEL, silent=False):
    return app_check_allowed(project.application, request_user, level, silent)


def app_check_allowed(application, request_user,
                      level=OWNER_LEVEL, silent=False):
    checks = (f(request_user, application) for f in ALLOWED_CHECKS[:level+1])
    return _check_yield(any(checks), silent)


def checkAlive(project):
    if not project.is_alive:
        m = _(astakos_messages.NOT_ALIVE_PROJECT) % project.id
        raise ProjectConflict(m)


def accept_membership_project_checks(project, request_user):
    project_check_allowed(project, request_user)
    checkAlive(project)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_JOIN_POLICY_CLOSED)
        raise ProjectConflict(m)

    if project.violates_members_limit(adding=1):
        m = _(astakos_messages.MEMBER_NUMBER_LIMIT_REACHED)
        raise ProjectConflict(m)


def accept_membership_checks(membership, request_user):
    if not membership.check_action("accept"):
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise ProjectConflict(m)

    project = membership.project
    accept_membership_project_checks(project, request_user)


def accept_membership(memb_id, request_user=None, reason=None):
    project = get_project_of_membership_for_update(memb_id)
    membership = get_membership_by_id(memb_id)
    accept_membership_checks(membership, request_user)
    user = membership.person
    membership.perform_action("accept", actor=request_user, reason=reason)
    qh_sync_user(user)
    logger.info("User %s has been accepted in %s." %
                (user.log_display, project))

    membership_change_notify(project, user, 'accepted')
    return membership


def reject_membership_checks(membership, request_user):
    if not membership.check_action("reject"):
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise ProjectConflict(m)

    project = membership.project
    project_check_allowed(project, request_user)
    checkAlive(project)


def reject_membership(memb_id, request_user=None, reason=None):
    project = get_project_of_membership_for_update(memb_id)
    membership = get_membership_by_id(memb_id)
    reject_membership_checks(membership, request_user)
    user = membership.person
    membership.perform_action("reject", actor=request_user, reason=reason)
    logger.info("Request of user %s for %s has been rejected." %
                (user.log_display, project))

    membership_change_notify(project, user, 'rejected')
    return membership


def cancel_membership_checks(membership, request_user):
    if not membership.check_action("cancel"):
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise ProjectConflict(m)

    membership_check_allowed(membership, request_user, level=ADMIN_LEVEL)
    project = membership.project
    checkAlive(project)


def cancel_membership(memb_id, request_user, reason=None):
    project = get_project_of_membership_for_update(memb_id)
    membership = get_membership_by_id(memb_id)
    cancel_membership_checks(membership, request_user)
    membership.perform_action("cancel", actor=request_user, reason=reason)
    logger.info("Request of user %s for %s has been cancelled." %
                (membership.person.log_display, project))


def remove_membership_checks(membership, request_user=None):
    if not membership.check_action("remove"):
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise ProjectConflict(m)

    project = membership.project
    project_check_allowed(project, request_user)
    checkAlive(project)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED)
        raise ProjectConflict(m)


def remove_membership(memb_id, request_user=None, reason=None):
    project = get_project_of_membership_for_update(memb_id)
    membership = get_membership_by_id(memb_id)
    remove_membership_checks(membership, request_user)
    user = membership.person
    membership.perform_action("remove", actor=request_user, reason=reason)
    qh_sync_user(user)
    logger.info("User %s has been removed from %s." %
                (user.log_display, project))

    membership_change_notify(project, user, 'removed')
    return membership


def enroll_member(project_id, user, request_user=None, reason=None):
    project = get_project_for_update(project_id)
    try:
        project = get_project_for_update(project_id)
    except ProjectNotFound as e:
        raise ProjectConflict(e.message)
    accept_membership_project_checks(project, request_user)

    try:
        membership = get_membership(project_id, user.id)
        if not membership.check_action("enroll"):
            m = _(astakos_messages.MEMBERSHIP_ACCEPTED)
            raise ProjectConflict(m)
        membership.perform_action("join", actor=request_user, reason=reason)
    except ProjectNotFound:
        membership = new_membership(project, user, actor=request_user)

    membership.perform_action("accept", actor=request_user, reason=reason)
    qh_sync_user(user)
    logger.info("User %s has been enrolled in %s." %
                (membership.person.log_display, project))

    membership_enroll_notify(project, membership.person)
    return membership


def leave_project_checks(membership, request_user):
    if not membership.check_action("leave"):
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise ProjectConflict(m)

    membership_check_allowed(membership, request_user, level=ADMIN_LEVEL)
    project = membership.project
    checkAlive(project)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED)
        raise ProjectConflict(m)


def can_leave_request(project, user):
    m = user.get_membership(project)
    if m is None:
        return False
    try:
        leave_project_checks(m, user)
    except ProjectError:
        return False
    return True


def leave_project(memb_id, request_user, reason=None):
    project = get_project_of_membership_for_update(memb_id)
    membership = get_membership_by_id(memb_id)
    leave_project_checks(membership, request_user)

    auto_accepted = False
    leave_policy = project.application.member_leave_policy
    if leave_policy == AUTO_ACCEPT_POLICY:
        membership.perform_action("remove", actor=request_user, reason=reason)
        qh_sync_user(request_user)
        logger.info("User %s has left %s." %
                    (request_user.log_display, project))
        auto_accepted = True
    else:
        membership.perform_action("leave_request", actor=request_user,
                                  reason=reason)
        logger.info("User %s requested to leave %s." %
                    (request_user.log_display, project))
        membership_leave_request_notify(project, membership.person)
    return auto_accepted


def join_project_checks(project):
    checkAlive(project)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_JOIN_POLICY_CLOSED)
        raise ProjectConflict(m)


def can_join_request(project, user):
    try:
        join_project_checks(project)
    except ProjectError:
        return False

    m = user.get_membership(project)
    if not m:
        return True
    return m.check_action("join")


def new_membership(project, user, actor=None, reason=None):
    m = ProjectMembership.objects.create(project=project, person=user)
    m._log_create(None, ProjectMembership.REQUESTED, actor=actor,
                  reason=reason)
    return m


def join_project(project_id, request_user, reason=None):
    project = get_project_for_update(project_id)
    join_project_checks(project)

    try:
        membership = get_membership(project.id, request_user.id)
        if not membership.check_action("join"):
            msg = _(astakos_messages.MEMBERSHIP_ASSOCIATED)
            raise ProjectConflict(msg)
        membership.perform_action("join", actor=request_user, reason=reason)
    except ProjectNotFound:
        membership = new_membership(project, request_user, actor=request_user,
                                    reason=reason)

    join_policy = project.application.member_join_policy
    if (join_policy == AUTO_ACCEPT_POLICY and (
            not project.violates_members_limit(adding=1))):
        membership.perform_action("accept", actor=request_user, reason=reason)
        qh_sync_user(request_user)
        logger.info("User %s joined %s." %
                    (request_user.log_display, project))
    else:
        membership_request_notify(project, membership.person)
        logger.info("User %s requested to join %s." %
                    (request_user.log_display, project))
    return membership


MEMBERSHIP_ACTION_CHECKS = {
    "leave":  leave_project_checks,
    "cancel": cancel_membership_checks,
    "accept": accept_membership_checks,
    "reject": reject_membership_checks,
    "remove": remove_membership_checks,
}


def membership_allowed_actions(membership, request_user):
    allowed = []
    for action, check in MEMBERSHIP_ACTION_CHECKS.iteritems():
        try:
            check(membership, request_user)
            allowed.append(action)
        except ProjectError:
            pass
    return allowed


def submit_application(owner=None,
                       name=None,
                       project_id=None,
                       homepage=None,
                       description=None,
                       start_date=None,
                       end_date=None,
                       member_join_policy=None,
                       member_leave_policy=None,
                       limit_on_members_number=None,
                       comments=None,
                       resources=None,
                       request_user=None):

    project = None
    if project_id is not None:
        project = get_project_for_update(project_id)
        project_check_allowed(project, request_user, level=APPLICANT_LEVEL)

    policies = validate_resource_policies(resources)

    force = request_user.is_project_admin()
    ok, limit = qh_add_pending_app(owner, project, force)
    if not ok:
        m = _(astakos_messages.REACHED_PENDING_APPLICATION_LIMIT) % limit
        raise ProjectConflict(m)

    application = ProjectApplication(
        applicant=request_user,
        owner=owner,
        name=name,
        homepage=homepage,
        description=description,
        start_date=start_date,
        end_date=end_date,
        member_join_policy=member_join_policy,
        member_leave_policy=member_leave_policy,
        limit_on_members_number=limit_on_members_number,
        comments=comments)

    if project is None:
        chain = new_chain()
        application.chain_id = chain.chain
        application.save()
        Project.objects.create(id=chain.chain, application=application)
    else:
        application.chain = project
        application.save()
        if project.application.state != ProjectApplication.APPROVED:
            project.application = application
            project.save()

        pending = ProjectApplication.objects.filter(
            chain=project,
            state=ProjectApplication.PENDING).exclude(id=application.id)
        for app in pending:
            app.state = ProjectApplication.REPLACED
            app.save()

    if policies is not None:
        set_resource_policies(application, policies)
    logger.info("User %s submitted %s." %
                (request_user.log_display, application.log_display))
    application_submit_notify(application)
    return application


def validate_resource_policies(policies):
    if not isinstance(policies, dict):
        raise ProjectBadRequest("Malformed resource policies")

    resource_names = policies.keys()
    resources = Resource.objects.filter(name__in=resource_names)
    resource_d = {}
    for resource in resources:
        resource_d[resource.name] = resource

    found = resource_d.keys()
    nonex = [name for name in resource_names if name not in found]
    if nonex:
        raise ProjectBadRequest("Malformed resource policies")

    pols = []
    for resource_name, specs in policies.iteritems():
        p_capacity = specs.get("project_capacity")
        m_capacity = specs.get("member_capacity")

        if p_capacity is not None and not isinstance(p_capacity, (int, long)):
            raise ProjectBadRequest("Malformed resource policies")
        if not isinstance(m_capacity, (int, long)):
            raise ProjectBadRequest("Malformed resource policies")
        pols.append((resource_d[resource_name], m_capacity, p_capacity))
    return pols


def set_resource_policies(application, policies):
    for resource, m_capacity, p_capacity in policies:
        g = application.projectresourcegrant_set
        g.create(resource=resource,
                 member_capacity=m_capacity,
                 project_capacity=p_capacity)


def cancel_application(application_id, request_user=None, reason=""):
    get_project_of_application_for_update(application_id)
    application = get_application(application_id)
    app_check_allowed(application, request_user, level=APPLICANT_LEVEL)

    if not application.can_cancel():
        m = _(astakos_messages.APPLICATION_CANNOT_CANCEL %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    qh_release_pending_app(application.owner)

    application.cancel(actor=request_user, reason=reason)
    logger.info("%s has been cancelled." % (application.log_display))


def dismiss_application(application_id, request_user=None, reason=""):
    get_project_of_application_for_update(application_id)
    application = get_application(application_id)
    app_check_allowed(application, request_user, level=APPLICANT_LEVEL)

    if not application.can_dismiss():
        m = _(astakos_messages.APPLICATION_CANNOT_DISMISS %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    application.dismiss(actor=request_user, reason=reason)
    logger.info("%s has been dismissed." % (application.log_display))


def deny_application(application_id, request_user=None, reason=""):
    get_project_of_application_for_update(application_id)
    application = get_application(application_id)

    app_check_allowed(application, request_user, level=ADMIN_LEVEL)

    if not application.can_deny():
        m = _(astakos_messages.APPLICATION_CANNOT_DENY %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    qh_release_pending_app(application.owner)

    application.deny(actor=request_user, reason=reason)
    logger.info("%s has been denied with reason \"%s\"." %
                (application.log_display, reason))
    application_deny_notify(application)


def check_conflicting_projects(application):
    project = application.chain
    new_project_name = application.name
    try:
        q = Q(name=new_project_name) & ~Q(state=Project.TERMINATED)
        conflicting_project = Project.objects.get(q)
        if (conflicting_project != project):
            m = (_("cannot approve: project with name '%s' "
                   "already exists (id: %s)") %
                 (new_project_name, conflicting_project.id))
            raise ProjectConflict(m)  # invalid argument
    except Project.DoesNotExist:
        pass


def approve_application(app_id, request_user=None, reason=""):
    get_project_lock()
    project = get_project_of_application_for_update(app_id)
    application = get_application(app_id)

    app_check_allowed(application, request_user, level=ADMIN_LEVEL)

    if not application.can_approve():
        m = _(astakos_messages.APPLICATION_CANNOT_APPROVE %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    check_conflicting_projects(application)

    # Pre-lock members and owner together in order to impose an ordering
    # on locking users
    members = members_to_sync(project)
    uids_to_sync = [member.id for member in members]
    owner = application.owner
    uids_to_sync.append(owner.id)
    get_users_for_update(uids_to_sync)

    qh_release_pending_app(owner, locked=True)
    application.approve(actor=request_user, reason=reason)
    project.application = application
    project.name = application.name
    project.save()
    if project.is_deactivated():
        project.resume(actor=request_user, reason="APPROVE")
    qh_sync_locked_users(members)
    logger.info("%s has been approved." % (application.log_display))
    application_approve_notify(application)


def check_expiration(execute=False):
    objects = Project.objects
    expired = objects.expired_projects()
    if execute:
        for project in expired:
            terminate(project.pk)

    return [project.expiration_info() for project in expired]


def terminate(project_id, request_user=None, reason=None):
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)
    checkAlive(project)

    project.terminate(actor=request_user, reason=reason)
    qh_sync_project(project)
    logger.info("%s has been terminated." % (project))

    project_termination_notify(project)


def suspend(project_id, request_user=None, reason=None):
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)
    checkAlive(project)

    project.suspend(actor=request_user, reason=reason)
    qh_sync_project(project)
    logger.info("%s has been suspended." % (project))

    project_suspension_notify(project)


def unsuspend(project_id, request_user=None, reason=None):
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)

    if not project.is_suspended:
        m = _(astakos_messages.NOT_SUSPENDED_PROJECT) % project.id
        raise ProjectConflict(m)

    project.resume(actor=request_user, reason=reason)
    qh_sync_project(project)
    logger.info("%s has been unsuspended." % (project))
    project_unsuspension_notify(project)


def reinstate(project_id, request_user=None, reason=None):
    get_project_lock()
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)

    if not project.is_terminated:
        m = _(astakos_messages.NOT_TERMINATED_PROJECT) % project.id
        raise ProjectConflict(m)

    check_conflicting_projects(project.application)
    project.resume(actor=request_user, reason=reason)
    qh_sync_project(project)
    logger.info("%s has been reinstated" % (project))
    project_reinstatement_notify(project)


def _partition_by(f, l):
    d = {}
    for x in l:
        group = f(x)
        group_l = d.get(group, [])
        group_l.append(x)
        d[group] = group_l
    return d


def count_pending_app(users):
    users = list(users)
    apps = ProjectApplication.objects.filter(state=ProjectApplication.PENDING,
                                             owner__in=users)
    apps_d = _partition_by(lambda a: a.owner.uuid, apps)

    usage = {}
    for user in users:
        uuid = user.uuid
        usage[uuid] = len(apps_d.get(uuid, []))
    return usage


def get_pending_app_diff(user, project):
    if project is None:
        diff = 1
    else:
        objs = ProjectApplication.objects
        q = objs.filter(chain=project, state=ProjectApplication.PENDING)
        count = q.count()
        diff = 1 - count
    return diff


def qh_add_pending_app(user, project=None, force=False):
    user = AstakosUser.forupdate.get_for_update(id=user.id)
    diff = get_pending_app_diff(user, project)
    return register_pending_apps(user, diff, force)


def check_pending_app_quota(user, project=None):
    diff = get_pending_app_diff(user, project)
    quota = get_pending_app_quota(user)
    limit = quota['limit']
    usage = quota['usage']
    if usage + diff > limit:
        return False, limit
    return True, None


def qh_release_pending_app(user, locked=False):
    if not locked:
        user = AstakosUser.forupdate.get_for_update(id=user.id)
    register_pending_apps(user, -1)

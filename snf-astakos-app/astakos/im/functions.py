# Copyright 2011-2014 GRNET S.A. All rights reserved.
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
from dateutil.relativedelta import relativedelta

from django.utils.translation import ugettext as _
from django.core.mail import send_mail, get_connection
from django.core.urlresolvers import reverse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.db.models import Q

from synnefo_branding.utils import render_to_string

from synnefo.lib import join_urls
from astakos.im.models import AstakosUser, Invitation, ProjectMembership, \
    ProjectApplication, Project, new_chain, Resource, ProjectLock, \
    create_project, ProjectResourceQuota, ProjectResourceGrant
from astakos.im import quotas
from astakos.im import project_notif
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
    user.delete_online_access_tokens()
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
    logger.info("Sent user verification email: %s", user.log_display)


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
    msg = 'Sent helpdesk admin notification for %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.email)


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
    msg = 'Sent greeting %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.log_display)


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
    msg = 'Sent feedback from %s'
    logger.log(settings.LOGGING_LEVEL, msg, user.log_display)


def send_change_email(ec, request,
                      email_template_name=
                      'registration/email_change_email.txt'):
    url = ec.get_url()
    url = request.build_absolute_uri(url)
    c = {'url': url,
         'site_name': settings.SITENAME,
         'support': settings.CONTACT_EMAIL,
         'ec': ec}
    message = render_to_string(email_template_name, c)
    from_email = settings.SERVER_EMAIL
    send_mail(_(astakos_messages.EMAIL_CHANGE_EMAIL_SUBJECT), message,
              from_email,
              [ec.new_email_address], connection=get_connection())
    msg = 'Sent change email for %s'
    logger.log(settings.LOGGING_LEVEL, msg, ec.user.log_display)


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
        return Project.objects.select_related(
            "application", "application__owner",
            "application__applicant").get(id=project_id)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id
        raise ProjectNotFound(m)


def get_project_by_uuid(uuid):
    try:
        return Project.objects.get(uuid=uuid)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % uuid
        raise ProjectNotFound(m)


def get_project_for_update(project_id):
    try:
        try:
            project_id = int(project_id)
            return Project.objects.select_for_update().get(id=project_id)
        except ValueError:
            return Project.objects.select_for_update().get(uuid=project_id)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id
        raise ProjectNotFound(m)


def get_project_of_application_for_update(app_id):
    app = get_application(app_id)
    return get_project_for_update(app.chain_id)


def get_project_lock():
    ProjectLock.objects.select_for_update().get(pk=1)


def get_application(application_id):
    try:
        return ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) % application_id
        raise ProjectNotFound(m)


def get_project_of_membership_for_update(memb_id):
    m = get_membership_by_id(memb_id)
    return get_project_for_update(m.project_id)


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


ADMIN_LEVEL = 0
OWNER_LEVEL = 1
APPLICANT_LEVEL = 1
ANY_LEVEL = 2


def is_admin(user):
    return not user or user.is_project_admin()


def _failure(silent=False):
    if silent:
        return False

    m = _(astakos_messages.NOT_ALLOWED)
    raise ProjectForbidden(m)


def membership_check_allowed(membership, request_user,
                             level=OWNER_LEVEL, silent=False):
    r = project_check_allowed(
        membership.project, request_user, level, silent=True)

    if r or membership.person == request_user:
        return True
    return _failure(silent)


def project_check_allowed(project, request_user,
                          level=OWNER_LEVEL, silent=False):
    if is_admin(request_user):
        return True
    if level <= ADMIN_LEVEL:
        return _failure(silent)

    if project.owner == request_user:
        return True
    if level <= OWNER_LEVEL:
        return _failure(silent)

    if project.state == Project.NORMAL and not project.private \
            or bool(project.projectmembership_set.any_accepted().
                    filter(person=request_user)):
            return True
    return _failure(silent)


def app_check_allowed(application, request_user,
                      level=OWNER_LEVEL, silent=False):
    if is_admin(request_user):
        return True
    if level <= ADMIN_LEVEL:
        return _failure(silent)

    if application.applicant == request_user:
        return True
    return _failure(silent)


def checkAlive(project):
    if not project.is_alive:
        m = _(astakos_messages.NOT_ALIVE_PROJECT) % project.uuid
        raise ProjectConflict(m)


def accept_membership_project_checks(project, request_user):
    project_check_allowed(project, request_user)
    checkAlive(project)

    join_policy = project.member_join_policy
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
    quotas.qh_sync_membership(membership)
    logger.info("User %s has been accepted in %s." %
                (user.log_display, project))

    project_notif.membership_change_notify(project, user, 'accepted')
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

    project_notif.membership_change_notify(project, user, 'rejected')
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

    leave_policy = project.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED)
        raise ProjectConflict(m)


def remove_membership(memb_id, request_user=None, reason=None):
    project = get_project_of_membership_for_update(memb_id)
    membership = get_membership_by_id(memb_id)
    remove_membership_checks(membership, request_user)
    user = membership.person
    membership.perform_action("remove", actor=request_user, reason=reason)
    quotas.qh_sync_membership(membership)
    logger.info("User %s has been removed from %s." %
                (user.log_display, project))

    project_notif.membership_change_notify(project, user, 'removed')
    return membership


def enroll_member_by_email(project_id, email, request_user=None, reason=None):
    try:
        user = AstakosUser.objects.accepted().get(email=email)
        return enroll_member(project_id, user, request_user, reason=reason)
    except AstakosUser.DoesNotExist:
        raise ProjectConflict(astakos_messages.UNKNOWN_USERS % email)


def enroll_member(project_id, user, request_user=None, reason=None):
    try:
        project = get_project_for_update(project_id)
    except ProjectNotFound as e:
        raise ProjectConflict(e.message)
    accept_membership_project_checks(project, request_user)

    try:
        membership = get_membership(project.id, user.id)
        if not membership.check_action("enroll"):
            m = _(astakos_messages.MEMBERSHIP_ACCEPTED)
            raise ProjectConflict(m)
        membership.perform_action("enroll", actor=request_user, reason=reason)
    except ProjectNotFound:
        membership = new_membership(project, user, actor=request_user,
                                    enroll=True)

    quotas.qh_sync_membership(membership)
    logger.info("User %s has been enrolled in %s." %
                (membership.person.log_display, project))

    project_notif.membership_enroll_notify(project, membership.person)
    return membership


def leave_project_checks(membership, request_user):
    if not membership.check_action("leave"):
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise ProjectConflict(m)

    membership_check_allowed(membership, request_user, level=ADMIN_LEVEL)
    project = membership.project
    checkAlive(project)

    leave_policy = project.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED)
        raise ProjectConflict(m)


def can_cancel_join_request(project, user):
    m = user.get_membership(project)
    if m is None:
        return False
    return m.state in [m.REQUESTED]


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
    leave_policy = project.member_leave_policy
    if leave_policy == AUTO_ACCEPT_POLICY:
        membership.perform_action("remove", actor=request_user, reason=reason)
        quotas.qh_sync_membership(membership)
        logger.info("User %s has left %s." %
                    (request_user.log_display, project))
        auto_accepted = True
    else:
        membership.perform_action("leave_request", actor=request_user,
                                  reason=reason)
        logger.info("User %s requested to leave %s." %
                    (request_user.log_display, project))
        project_notif.membership_request_notify(
            project, membership.person, "leave")
    return auto_accepted


def join_project_checks(project):
    checkAlive(project)

    join_policy = project.member_join_policy
    if join_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_JOIN_POLICY_CLOSED)
        raise ProjectConflict(m)


Nothing = type('Nothing', (), {})


def can_join_request(project, user, membership=Nothing):
    try:
        join_project_checks(project)
    except ProjectError:
        return False

    m = (membership if membership is not Nothing
         else user.get_membership(project))
    if not m:
        return True
    return m.check_action("join")


def new_membership(project, user, actor=None, reason=None, enroll=False):
    state = (ProjectMembership.ACCEPTED if enroll
             else ProjectMembership.REQUESTED)
    m = ProjectMembership.objects.create(
        project=project, person=user, state=state, initialized=enroll)
    m._log_create(None, state, actor=actor, reason=reason)
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

    join_policy = project.member_join_policy
    if (join_policy == AUTO_ACCEPT_POLICY and (
            not project.violates_members_limit(adding=1))):
        membership.perform_action("accept", actor=request_user, reason=reason)
        quotas.qh_sync_membership(membership)
        logger.info("User %s joined %s." %
                    (request_user.log_display, project))
    else:
        project_notif.membership_request_notify(
            project, membership.person, "join")
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


def make_base_project(username):
    chain = new_chain()
    proj = create_project(
        id=chain.chain,
        last_application=None,
        owner=None,
        realname="tmp",
        homepage="",
        description=("base project for user " + username),
        end_date=(datetime.now() + relativedelta(years=100)),
        member_join_policy=CLOSED_POLICY,
        member_leave_policy=CLOSED_POLICY,
        limit_on_members_number=1,
        private=True,
        is_base=True)
    proj.realname = "base:" + proj.uuid
    proj.save()
    # No quota are set; they will be filled in upon user acceptance
    return proj


def enable_base_project(user):
    project = user.base_project
    _fill_from_skeleton(project)
    project.activate()
    new_membership(project, user, enroll=True)
    quotas.qh_sync_project(project)


MODIFY_KEYS_MAIN = ["owner", "realname", "homepage", "description"]
MODIFY_KEYS_EXTRA = ["end_date", "member_join_policy", "member_leave_policy",
                     "limit_on_members_number", "private"]
MODIFY_KEYS = MODIFY_KEYS_MAIN + MODIFY_KEYS_EXTRA


def modifies_main_fields(request):
    return set(request.keys()).intersection(MODIFY_KEYS_MAIN)


def modify_project(project_id, request):
    project = get_project_for_update(project_id)
    if project.state not in Project.INITIALIZED_STATES:
        m = _(astakos_messages.UNINITIALIZED_NO_MODIFY) % project.uuid
        raise ProjectConflict(m)

    if project.is_base:
        main_fields = modifies_main_fields(request)
        if main_fields:
            m = (_(astakos_messages.BASE_NO_MODIFY_FIELDS)
                 % ", ".join(map(unicode, main_fields)))
            raise ProjectBadRequest(m)

    new_name = request.get("realname")
    if new_name is not None and project.is_alive:
        check_conflicting_projects(project, new_name)
        project.realname = new_name
        project.name = new_name
        project.save()

    _modify_projects(Project.objects.filter(id=project.id), request)


def modify_projects_in_bulk(flt, request):
    main_fields = modifies_main_fields(request)
    if main_fields:
        raise ProjectBadRequest("Cannot modify field(s) '%s' in bulk" %
                                ", ".join(map(unicode, main_fields)))

    projects = Project.objects.initialized(flt).select_for_update()
    _modify_projects(projects, request)


def _modify_projects(projects, request):
    upds = {}
    for key in MODIFY_KEYS:
        value = request.get(key)
        if value is not None:
            upds[key] = value
    projects.update(**upds)

    changed_resources = set()
    pquotas = []
    req_policies = request.get("resources", {})
    req_policies = validate_resource_policies(req_policies, admin=True)
    for project in projects:
        for resource, m_capacity, p_capacity in req_policies:
            changed_resources.add(resource)
            pquotas.append(
                ProjectResourceQuota(
                    project=project,
                    resource=resource,
                    member_capacity=m_capacity,
                    project_capacity=p_capacity))
    ProjectResourceQuota.objects.\
        filter(project__in=projects, resource__in=changed_resources).delete()
    ProjectResourceQuota.objects.bulk_create(pquotas)
    quotas.qh_sync_projects(projects)


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
                       private=False,
                       comments=None,
                       resources=None,
                       request_user=None):

    project = None
    if project_id is not None:
        project = get_project_for_update(project_id)
        project_check_allowed(project, request_user, level=APPLICANT_LEVEL)
        if project.state not in Project.INITIALIZED_STATES:
            raise ProjectConflict("Cannot modify an uninitialized project.")

    policies = validate_resource_policies(resources)

    force = request_user.is_project_admin()
    ok, limit = qh_add_pending_app(request_user, project, force)
    if not ok:
        m = _(astakos_messages.REACHED_PENDING_APPLICATION_LIMIT) % limit
        raise ProjectConflict(m)

    if project is None:
        chain = new_chain()
        project = create_project(
            id=chain.chain,
            owner=owner,
            realname=name,
            homepage=homepage,
            description=description,
            end_date=end_date,
            member_join_policy=member_join_policy,
            member_leave_policy=member_leave_policy,
            limit_on_members_number=limit_on_members_number,
            private=private)
        if policies is not None:
            set_project_resources(project, policies)

    application = ProjectApplication.objects.create(
        applicant=request_user,
        chain=project,
        owner=owner,
        name=name,
        homepage=homepage,
        description=description,
        start_date=start_date,
        end_date=end_date,
        member_join_policy=member_join_policy,
        member_leave_policy=member_leave_policy,
        limit_on_members_number=limit_on_members_number,
        private=private,
        comments=comments)
    if policies is not None:
        set_application_resources(application, policies)

    project.last_application = application
    project.save()

    ProjectApplication.objects.\
        filter(chain=project, state=ProjectApplication.PENDING).\
        exclude(id=application.id).\
        update(state=ProjectApplication.REPLACED)

    logger.info("User %s submitted %s." %
                (request_user.log_display, application.log_display))
    project_notif.application_notify(application, "submit")
    return application


def validate_resource_policies(policies, admin=False):
    if not isinstance(policies, dict):
        raise ProjectBadRequest("Malformed resource policies")

    resource_names = policies.keys()
    resources = Resource.objects.filter(name__in=resource_names)
    if not admin:
        resources = resources.filter(api_visible=True)

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

        if not isinstance(p_capacity, (int, long)) or \
                not isinstance(m_capacity, (int, long)):
            raise ProjectBadRequest("Malformed resource policies")
        pols.append((resource_d[resource_name], m_capacity, p_capacity))
    return pols


def set_application_resources(application, policies):
    grants = []
    for resource, m_capacity, p_capacity in policies:
        grants.append(
            ProjectResourceGrant(
                project_application=application,
                resource=resource,
                member_capacity=m_capacity,
                project_capacity=p_capacity))
    ProjectResourceGrant.objects.bulk_create(grants)


def set_project_resources(project, policies):
    grants = []
    for resource, m_capacity, p_capacity in policies:
        grants.append(
            ProjectResourceQuota(
                project=project,
                resource=resource,
                member_capacity=m_capacity,
                project_capacity=p_capacity))
    ProjectResourceQuota.objects.bulk_create(grants)


def check_app_relevant(application, project, project_id):
    if project_id is not None and project.uuid != project_id or \
            project.last_application != application:
        pid = project_id if project_id is not None else project.uuid
        m = (_("%s is not a pending application for project %s.") %
             (application.id, pid))
        raise ProjectConflict(m)


def cancel_application(application_id, project_id=None, request_user=None,
                       reason=""):
    project = get_project_of_application_for_update(application_id)
    application = get_application(application_id)
    check_app_relevant(application, project, project_id)
    app_check_allowed(application, request_user, level=APPLICANT_LEVEL)

    if not application.can_cancel():
        m = _(astakos_messages.APPLICATION_CANNOT_CANCEL %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    qh_release_pending_app(application.applicant)

    application.cancel(actor=request_user, reason=reason)
    if project.state == Project.UNINITIALIZED:
        project.set_deleted()
    logger.info("%s has been cancelled." % (application.log_display))


def dismiss_application(application_id, project_id=None, request_user=None,
                        reason=""):
    project = get_project_of_application_for_update(application_id)
    application = get_application(application_id)
    check_app_relevant(application, project, project_id)
    app_check_allowed(application, request_user, level=APPLICANT_LEVEL)

    if not application.can_dismiss():
        m = _(astakos_messages.APPLICATION_CANNOT_DISMISS %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    application.dismiss(actor=request_user, reason=reason)
    if project.state == Project.UNINITIALIZED:
        project.set_deleted()
    logger.info("%s has been dismissed." % (application.log_display))


def deny_application(application_id, project_id=None, request_user=None,
                     reason=""):
    project = get_project_of_application_for_update(application_id)
    application = get_application(application_id)
    check_app_relevant(application, project, project_id)
    app_check_allowed(application, request_user, level=ADMIN_LEVEL)

    if not application.can_deny():
        m = _(astakos_messages.APPLICATION_CANNOT_DENY %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    qh_release_pending_app(application.applicant)

    application.deny(actor=request_user, reason=reason)
    logger.info("%s has been denied with reason \"%s\"." %
                (application.log_display, reason))
    project_notif.application_notify(application, "deny")


def check_conflicting_projects(project, new_project_name):
    try:
        q = Q(name=new_project_name) & ~Q(id=project.id)
        conflicting_project = Project.objects.get(q)
        m = (_("cannot approve: project with name '%s' "
               "already exists (id: %s)") %
             (new_project_name, conflicting_project.uuid))
        raise ProjectConflict(m)  # invalid argument
    except Project.DoesNotExist:
        pass


def approve_application(application_id, project_id=None, request_user=None,
                        reason=""):
    get_project_lock()
    project = get_project_of_application_for_update(application_id)
    application = get_application(application_id)
    check_app_relevant(application, project, project_id)
    app_check_allowed(application, request_user, level=ADMIN_LEVEL)

    if not application.can_approve():
        m = _(astakos_messages.APPLICATION_CANNOT_APPROVE %
              (application.id, application.state_display()))
        raise ProjectConflict(m)

    if application.name:
        check_conflicting_projects(project, application.name)

    qh_release_pending_app(application.applicant)
    application.approve(actor=request_user, reason=reason)

    if project.state == Project.UNINITIALIZED:
        _fill_from_skeleton(project)
    else:
        _apply_modifications(project, application)
    project.activate(actor=request_user, reason=reason)

    quotas.qh_sync_project(project)
    logger.info("%s has been approved." % (application.log_display))
    project_notif.application_notify(application, "approve")
    return project


def _fill_from_skeleton(project):
    current_resources = set(ProjectResourceQuota.objects.
                            filter(project=project).
                            values_list("resource_id", flat=True))
    resources = Resource.objects.all()
    new_quotas = []
    for resource in resources:
        if resource.id not in current_resources:
            limit = quotas.pick_limit_scheme(project, resource)
            new_quotas.append(
                ProjectResourceQuota(
                    project=project,
                    resource=resource,
                    member_capacity=limit,
                    project_capacity=limit))
    ProjectResourceQuota.objects.bulk_create(new_quotas)


def _apply_modifications(project, application):
    FIELDS = [
        ("owner", "owner"),
        ("name", "realname"),
        ("homepage", "homepage"),
        ("description", "description"),
        ("end_date", "end_date"),
        ("member_join_policy", "member_join_policy"),
        ("member_leave_policy", "member_leave_policy"),
        ("limit_on_members_number", "limit_on_members_number"),
        ("private", "private"),
        ]

    changed = False
    for appfield, projectfield in FIELDS:
        value = getattr(application, appfield)
        if value is not None:
            changed = True
            setattr(project, projectfield, value)
    if changed:
        project.save()

    grants = application.projectresourcegrant_set.all()
    pquotas = []
    resources = []
    for grant in grants:
        resources.append(grant.resource)
        pquotas.append(
            ProjectResourceQuota(
                project=project,
                resource=grant.resource,
                member_capacity=grant.member_capacity,
                project_capacity=grant.project_capacity))
    ProjectResourceQuota.objects.\
        filter(project=project, resource__in=resources).delete()
    ProjectResourceQuota.objects.bulk_create(pquotas)


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
    if project.is_base:
        m = _(astakos_messages.BASE_NO_TERMINATE) % project.uuid
        raise ProjectConflict(m)

    project.terminate(actor=request_user, reason=reason)
    quotas.qh_sync_project(project)
    logger.info("%s has been terminated." % (project))

    project_notif.project_notify(project, "terminate")


def suspend(project_id, request_user=None, reason=None):
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)
    checkAlive(project)

    project.suspend(actor=request_user, reason=reason)
    quotas.qh_sync_project(project)
    logger.info("%s has been suspended." % (project))

    project_notif.project_notify(project, "suspend")


def unsuspend(project_id, request_user=None, reason=None):
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)

    if not project.is_suspended:
        m = _(astakos_messages.NOT_SUSPENDED_PROJECT) % project.uuid
        raise ProjectConflict(m)

    project.resume(actor=request_user, reason=reason)
    quotas.qh_sync_project(project)
    logger.info("%s has been unsuspended." % (project))
    project_notif.project_notify(project, "unsuspend")


def reinstate(project_id, request_user=None, reason=None):
    get_project_lock()
    project = get_project_for_update(project_id)
    project_check_allowed(project, request_user, level=ADMIN_LEVEL)

    if not project.is_terminated:
        m = _(astakos_messages.NOT_TERMINATED_PROJECT) % project.uuid
        raise ProjectConflict(m)

    check_conflicting_projects(project, project.realname)
    project.resume(actor=request_user, reason=reason)
    quotas.qh_sync_project(project)
    logger.info("%s has been reinstated" % (project))
    project_notif.project_notify(project, "reinstate")


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

    usage = quotas.QuotaDict()
    for user in users:
        uuid = user.uuid
        usage[uuid][user.base_project.uuid][quotas.PENDING_APP_RESOURCE] = \
            len(apps_d.get(uuid, []))
    return usage


def get_pending_app_diff(project):
    if project is None:
        diff = 1
    else:
        objs = ProjectApplication.objects
        q = objs.filter(chain=project, state=ProjectApplication.PENDING)
        count = q.count()
        diff = 1 - count
    return diff


def qh_add_pending_app(user, project=None, force=False, assign_project=None):
    if assign_project is None:
        assign_project = user.base_project
    diff = get_pending_app_diff(project)
    return quotas.register_pending_apps(user, assign_project,
                                        diff, force=force)


def check_pending_app_quota(user, project=None):
    diff = get_pending_app_diff(project)
    quota = quotas.get_pending_app_quota(user)
    limit = quota['limit']
    usage = quota['usage']
    if usage + diff > limit:
        return False, limit
    return True, None


def qh_release_pending_app(user, assign_project=None):
    if assign_project is None:
        assign_project = user.base_project
    quotas.register_pending_apps(user, assign_project, -1)

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

from django.utils.translation import ugettext as _
from django.core.mail import send_mail, get_connection
from django.core.urlresolvers import reverse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404

from synnefo_branding.utils import render_to_string

from synnefo.lib import join_urls
from astakos.im.models import AstakosUser, Invitation, ProjectMembership, \
    ProjectApplication, Project, Chain, new_chain
from astakos.im.quotas import qh_sync_user, get_pending_app_quota, \
    register_pending_apps, qh_sync_project, qh_sync_locked_users, \
    get_users_for_update, members_to_sync
from astakos.im.project_notif import membership_change_notify, \
    membership_enroll_notify, membership_request_notify, \
    membership_leave_request_notify, application_submit_notify, \
    application_approve_notify, application_deny_notify, \
    project_termination_notify, project_suspension_notify
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

AUTO_ACCEPT_POLICY = 1
MODERATED_POLICY = 2
CLOSED_POLICY = 3

POLICIES = [AUTO_ACCEPT_POLICY, MODERATED_POLICY, CLOSED_POLICY]


def get_project_by_application_id(project_application_id):
    try:
        return Project.objects.get(application__id=project_application_id)
    except Project.DoesNotExist:
        m = (_(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) %
             project_application_id)
        raise IOError(m)


def get_related_project_id(application_id):
    try:
        app = ProjectApplication.objects.get(id=application_id)
        chain = app.chain
        Project.objects.get(id=chain)
        return chain
    except (ProjectApplication.DoesNotExist, Project.DoesNotExist):
        return None


def get_chain_of_application_id(application_id):
    try:
        app = ProjectApplication.objects.get(id=application_id)
        chain = app.chain
        return chain.chain
    except ProjectApplication.DoesNotExist:
        return None


def get_project_by_id(project_id):
    try:
        return Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % project_id
        raise IOError(m)


def get_project_by_name(name):
    try:
        return Project.objects.get(name=name)
    except Project.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % name
        raise IOError(m)


def get_chain_for_update(chain_id):
    try:
        return Chain.objects.get_for_update(chain=chain_id)
    except Chain.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_ID) % chain_id
        raise IOError(m)


def get_chain_of_application_for_update(app_id):
    app = get_application(app_id)
    return Chain.objects.get_for_update(chain=app.chain_id)


def get_application(application_id):
    try:
        return ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_PROJECT_APPLICATION_ID) % application_id
        raise IOError(m)


def get_user_by_id(user_id):
    try:
        return AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_USER_ID) % user_id
        raise IOError(m)


def get_user_by_uuid(uuid):
    try:
        return AstakosUser.objects.get(uuid=uuid)
    except AstakosUser.DoesNotExist:
        m = _(astakos_messages.UNKNOWN_USER_ID) % uuid
        raise IOError(m)


def get_membership(project_id, user_id):
    try:
        objs = ProjectMembership.objects.select_related('project', 'person')
        return objs.get(project__id=project_id, person__id=user_id)
    except ProjectMembership.DoesNotExist:
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise IOError(m)


def get_membership_by_id(project_id, memb_id):
    try:
        objs = ProjectMembership.objects.select_related('project', 'person')
        return objs.get(project__id=project_id, id=memb_id)
    except ProjectMembership.DoesNotExist:
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise IOError(m)


def checkAllowed(entity, request_user, admin_only=False):
    if isinstance(entity, Project):
        application = entity.application
    elif isinstance(entity, ProjectApplication):
        application = entity
    else:
        m = "%s not a Project nor a ProjectApplication" % (entity,)
        raise ValueError(m)

    if not request_user or request_user.is_project_admin():
        return

    if not admin_only and application.owner == request_user:
        return

    m = _(astakos_messages.NOT_ALLOWED)
    raise PermissionDenied(m)


def checkAlive(project):
    if not project.is_alive:
        m = _(astakos_messages.NOT_ALIVE_PROJECT) % project.id
        raise PermissionDenied(m)


def accept_membership_checks(project, request_user):
    checkAllowed(project, request_user)
    checkAlive(project)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_JOIN_POLICY_CLOSED)
        raise PermissionDenied(m)

    if project.violates_members_limit(adding=1):
        m = _(astakos_messages.MEMBER_NUMBER_LIMIT_REACHED)
        raise PermissionDenied(m)


def accept_membership(project_id, memb_id, request_user=None):
    get_chain_for_update(project_id)

    membership = get_membership_by_id(project_id, memb_id)
    if not membership.can_accept():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    project = membership.project
    accept_membership_checks(project, request_user)
    user = membership.person
    membership.accept()
    qh_sync_user(user)
    logger.info("User %s has been accepted in %s." %
                (user.log_display, project))

    membership_change_notify(project, user, 'accepted')
    return membership


def reject_membership_checks(project, request_user):
    checkAllowed(project, request_user)
    checkAlive(project)


def reject_membership(project_id, memb_id, request_user=None):
    get_chain_for_update(project_id)

    membership = get_membership_by_id(project_id, memb_id)
    if not membership.can_reject():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    project = membership.project
    reject_membership_checks(project, request_user)
    user = membership.person
    membership.reject()
    logger.info("Request of user %s for %s has been rejected." %
                (user.log_display, project))

    membership_change_notify(project, user, 'rejected')
    return membership


def cancel_membership_checks(project):
    checkAlive(project)


def cancel_membership(project_id, request_user):
    get_chain_for_update(project_id)

    membership = get_membership(project_id, request_user.id)
    if not membership.can_cancel():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    project = membership.project
    cancel_membership_checks(project)
    membership.cancel()
    logger.info("Request of user %s for %s has been cancelled." %
                (membership.person.log_display, project))


def remove_membership_checks(project, request_user=None):
    checkAllowed(project, request_user)
    checkAlive(project)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED)
        raise PermissionDenied(m)


def remove_membership(project_id, memb_id, request_user=None):
    get_chain_for_update(project_id)

    membership = get_membership_by_id(project_id, memb_id)
    if not membership.can_remove():
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise PermissionDenied(m)

    project = membership.project
    remove_membership_checks(project, request_user)
    user = membership.person
    membership.remove()
    qh_sync_user(user)
    logger.info("User %s has been removed from %s." %
                (user.log_display, project))

    membership_change_notify(project, user, 'removed')
    return membership


def enroll_member(project_id, user, request_user=None):
    get_chain_for_update(project_id)
    project = get_project_by_id(project_id)
    accept_membership_checks(project, request_user)

    membership, created = ProjectMembership.objects.get_or_create(
        project=project,
        person=user)

    if not membership.can_accept():
        m = _(astakos_messages.NOT_MEMBERSHIP_REQUEST)
        raise PermissionDenied(m)

    membership.accept()
    qh_sync_user(user)
    logger.info("User %s has been enrolled in %s." %
                (membership.person.log_display, project))

    membership_enroll_notify(project, membership.person)
    return membership


def leave_project_checks(project):
    checkAlive(project)

    leave_policy = project.application.member_leave_policy
    if leave_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_LEAVE_POLICY_CLOSED)
        raise PermissionDenied(m)


def can_leave_request(project, user):
    try:
        leave_project_checks(project)
    except PermissionDenied:
        return False
    m = user.get_membership(project)
    if m is None:
        return False
    return m.can_leave()


def leave_project(project_id, request_user):
    get_chain_for_update(project_id)

    membership = get_membership(project_id, request_user.id)
    if not membership.can_leave():
        m = _(astakos_messages.NOT_ACCEPTED_MEMBERSHIP)
        raise PermissionDenied(m)

    project = membership.project
    leave_project_checks(project)

    auto_accepted = False
    leave_policy = project.application.member_leave_policy
    if leave_policy == AUTO_ACCEPT_POLICY:
        membership.remove()
        qh_sync_user(request_user)
        logger.info("User %s has left %s." %
                    (request_user.log_display, project))
        auto_accepted = True
    else:
        membership.leave_request()
        logger.info("User %s requested to leave %s." %
                    (request_user.log_display, project))
        membership_leave_request_notify(project, membership.person)
    return auto_accepted


def join_project_checks(project):
    checkAlive(project)

    join_policy = project.application.member_join_policy
    if join_policy == CLOSED_POLICY:
        m = _(astakos_messages.MEMBER_JOIN_POLICY_CLOSED)
        raise PermissionDenied(m)


def can_join_request(project, user):
    try:
        join_project_checks(project)
    except PermissionDenied:
        return False

    m = user.get_membership(project)
    return not(m)


def join_project(project_id, request_user):
    get_chain_for_update(project_id)
    project = get_project_by_id(project_id)
    join_project_checks(project)

    membership, created = ProjectMembership.objects.get_or_create(
        project=project,
        person=request_user)

    if not created:
        msg = _(astakos_messages.MEMBERSHIP_REQUEST_EXISTS)
        raise PermissionDenied(msg)

    auto_accepted = False
    join_policy = project.application.member_join_policy
    if (join_policy == AUTO_ACCEPT_POLICY and (
            not project.violates_members_limit(adding=1))):
        membership.accept()
        qh_sync_user(request_user)
        logger.info("User %s joined %s." %
                    (request_user.log_display, project))
        auto_accepted = True
    else:
        membership_request_notify(project, membership.person)
        logger.info("User %s requested to join %s." %
                    (request_user.log_display, project))
    return auto_accepted


def submit_application(owner=None,
                       name=None,
                       precursor_id=None,
                       homepage=None,
                       description=None,
                       start_date=None,
                       end_date=None,
                       member_join_policy=None,
                       member_leave_policy=None,
                       limit_on_members_number=None,
                       comments=None,
                       resource_policies=None,
                       request_user=None):

    precursor = None
    if precursor_id is not None:
        get_chain_of_application_for_update(precursor_id)
        precursor = ProjectApplication.objects.get(id=precursor_id)

        if (request_user and
            (not precursor.owner == request_user and
             not request_user.is_superuser
             and not request_user.is_project_admin())):
            m = _(astakos_messages.NOT_ALLOWED)
            raise PermissionDenied(m)

    force = request_user.is_project_admin()
    ok, limit = qh_add_pending_app(owner, precursor, force)
    if not ok:
        m = _(astakos_messages.REACHED_PENDING_APPLICATION_LIMIT) % limit
        raise PermissionDenied(m)

    application = ProjectApplication(
        applicant=request_user,
        owner=owner,
        name=name,
        precursor_application_id=precursor_id,
        homepage=homepage,
        description=description,
        start_date=start_date,
        end_date=end_date,
        member_join_policy=member_join_policy,
        member_leave_policy=member_leave_policy,
        limit_on_members_number=limit_on_members_number,
        comments=comments)

    if precursor is None:
        application.chain = new_chain()
    else:
        chain = precursor.chain
        application.chain = chain
        objs = ProjectApplication.objects
        pending = objs.filter(chain=chain, state=ProjectApplication.PENDING)
        for app in pending:
            app.state = ProjectApplication.REPLACED
            app.save()

    application.save()
    if resource_policies is not None:
        application.set_resource_policies(resource_policies)
    logger.info("User %s submitted %s." %
                (request_user.log_display, application.log_display))
    application_submit_notify(application)
    return application


def cancel_application(application_id, request_user=None, reason=""):
    get_chain_of_application_for_update(application_id)
    application = get_application(application_id)
    checkAllowed(application, request_user)

    if not application.can_cancel():
        m = _(astakos_messages.APPLICATION_CANNOT_CANCEL %
              (application.id, application.state_display()))
        raise PermissionDenied(m)

    qh_release_pending_app(application.owner)

    application.cancel()
    logger.info("%s has been cancelled." % (application.log_display))


def dismiss_application(application_id, request_user=None, reason=""):
    get_chain_of_application_for_update(application_id)
    application = get_application(application_id)
    checkAllowed(application, request_user)

    if not application.can_dismiss():
        m = _(astakos_messages.APPLICATION_CANNOT_DISMISS %
              (application.id, application.state_display()))
        raise PermissionDenied(m)

    application.dismiss()
    logger.info("%s has been dismissed." % (application.log_display))


def deny_application(application_id, request_user=None, reason=""):
    get_chain_of_application_for_update(application_id)
    application = get_application(application_id)

    checkAllowed(application, request_user, admin_only=True)

    if not application.can_deny():
        m = _(astakos_messages.APPLICATION_CANNOT_DENY %
              (application.id, application.state_display()))
        raise PermissionDenied(m)

    qh_release_pending_app(application.owner)

    application.deny(reason)
    logger.info("%s has been denied with reason \"%s\"." %
                (application.log_display, reason))
    application_deny_notify(application)


def check_conflicting_projects(application):
    try:
        project = get_project_by_id(application.chain)
    except IOError:
        project = None

    new_project_name = application.name
    try:
        q = Q(name=new_project_name) & ~Q(state=Project.TERMINATED)
        conflicting_project = Project.objects.get(q)
        if (conflicting_project != project):
            m = (_("cannot approve: project with name '%s' "
                   "already exists (id: %s)") %
                 (new_project_name, conflicting_project.id))
            raise PermissionDenied(m)  # invalid argument
    except Project.DoesNotExist:
        pass

    return project


def approve_application(app_id, request_user=None, reason=""):
    get_chain_of_application_for_update(app_id)
    application = get_application(app_id)

    checkAllowed(application, request_user, admin_only=True)

    if not application.can_approve():
        m = _(astakos_messages.APPLICATION_CANNOT_APPROVE %
              (application.id, application.state_display()))
        raise PermissionDenied(m)

    project = check_conflicting_projects(application)

    # Pre-lock members and owner together in order to impose an ordering
    # on locking users
    members = members_to_sync(project) if project is not None else []
    uids_to_sync = [member.id for member in members]
    owner = application.owner
    uids_to_sync.append(owner.id)
    get_users_for_update(uids_to_sync)

    qh_release_pending_app(owner, locked=True)
    application.approve(reason)
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


def terminate(project_id, request_user=None):
    get_chain_for_update(project_id)
    project = get_project_by_id(project_id)
    checkAllowed(project, request_user, admin_only=True)
    checkAlive(project)

    project.terminate()
    qh_sync_project(project)
    logger.info("%s has been terminated." % (project))

    project_termination_notify(project)


def suspend(project_id, request_user=None):
    get_chain_for_update(project_id)
    project = get_project_by_id(project_id)
    checkAllowed(project, request_user, admin_only=True)
    checkAlive(project)

    project.suspend()
    qh_sync_project(project)
    logger.info("%s has been suspended." % (project))

    project_suspension_notify(project)


def resume(project_id, request_user=None):
    get_chain_for_update(project_id)
    project = get_project_by_id(project_id)
    checkAllowed(project, request_user, admin_only=True)

    if not project.is_suspended:
        m = _(astakos_messages.NOT_SUSPENDED_PROJECT) % project.id
        raise PermissionDenied(m)

    project.resume()
    qh_sync_project(project)
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


def get_pending_app_diff(user, precursor):
    if precursor is None:
        diff = 1
    else:
        chain = precursor.chain
        objs = ProjectApplication.objects
        q = objs.filter(chain=chain, state=ProjectApplication.PENDING)
        count = q.count()
        diff = 1 - count
    return diff


def qh_add_pending_app(user, precursor=None, force=False):
    user = AstakosUser.forupdate.get_for_update(id=user.id)
    diff = get_pending_app_diff(user, precursor)
    return register_pending_apps(user, diff, force)


def check_pending_app_quota(user, precursor=None):
    diff = get_pending_app_diff(user, precursor)
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

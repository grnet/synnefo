import logging
from django.utils.translation import ugettext as _
import astakos.im.settings as settings
from astakos.im.notifications import build_notification, NotificationError

logger = logging.getLogger(__name__)

MEM_CHANGE_NOTIF = {
    'subject' : _(settings.PROJECT_MEMBERSHIP_CHANGE_SUBJECT),
    'template': 'im/projects/project_membership_change_notification.txt',
    }

MEM_ENROLL_NOTIF = {
    'subject' : _(settings.PROJECT_MEMBERSHIP_ENROLL_SUBJECT),
    'template': 'im/projects/project_membership_enroll_notification.txt',
    }

SENDER = settings.SERVER_EMAIL
ADMINS = settings.ADMINS

def membership_change_notify(project, user, action):
    try:
        notification = build_notification(
            SENDER,
            [user.email],
            MEM_CHANGE_NOTIF['subject'] % project.__dict__,
            template= MEM_CHANGE_NOTIF['template'],
            dictionary={'object':project, 'action':action})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def membership_enroll_notify(project, user):
    try:
        notification = build_notification(
            SENDER,
            [user.email],
            MEM_ENROLL_NOTIF['subject'] % project.__dict__,
            template= MEM_ENROLL_NOTIF['template'],
            dictionary={'object':project})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def membership_request_notify(project, requested_user):
    try:
        notification = build_notification(
            SENDER,
            [project.application.owner.email],
            _(settings.PROJECT_MEMBERSHIP_REQUEST_SUBJECT) % project.__dict__,
            template= 'im/projects/project_membership_request_notification.txt',
            dictionary={'object':project, 'user':requested_user.realname})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def membership_leave_request_notify(project, requested_user):
    try:
        notification = build_notification(
            SENDER,
            [project.application.owner.email],
            _(settings.PROJECT_MEMBERSHIP_LEAVE_REQUEST_SUBJECT) % project.__dict__,
            template= 'im/projects/project_membership_leave_request_notification.txt',
            dictionary={'object':project, 'user':requested_user.realname})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def application_submit_notify(application):
    try:
        notification = build_notification(
            SENDER,
            [i[1] for i in ADMINS],
            _(settings.PROJECT_CREATION_SUBJECT) % application.__dict__,
            template='im/projects/project_creation_notification.txt',
            dictionary={'object':application})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def application_deny_notify(application):
    try:
        notification = build_notification(
            SENDER,
            [application.owner.email],
            _(settings.PROJECT_DENIED_SUBJECT) % application.__dict__,
            template='im/projects/project_denial_notification.txt',
            dictionary={'object':application})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def application_approve_notify(application):
    try:
        notification = build_notification(
            SENDER,
            [application.owner.email],
            _(settings.PROJECT_APPROVED_SUBJECT) % application.__dict__,
            template='im/projects/project_approval_notification.txt',
            dictionary={'object':application})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)

def project_termination_notify(project):
    try:
        notification = build_notification(
            SENDER,
            [project.application.owner.email],
            _(settings.PROJECT_TERMINATION_SUBJECT) % project.__dict__,
            template='im/projects/project_termination_notification.txt',
            dictionary={'object':project}
        ).send()
    except NotificationError, e:
        logger.error(e.message)

def project_suspension_notify(project):
    try:
        notification = build_notification(
            SENDER,
            [project.application.owner.email],
            _(settings.PROJECT_SUSPENSION_SUBJECT) % project.__dict__,
            template='im/projects/project_suspension_notification.txt',
            dictionary={'object':project}
        ).send()
    except NotificationError, e:
        logger.error(e.message)

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
from django.utils.translation import ugettext as _
from astakos.im import settings
from astakos.im.notifications import build_notification, NotificationError
from astakos.im import messages

logger = logging.getLogger(__name__)

MEM_CHANGE_NOTIF = {
    'subject':   _(messages.PROJECT_MEMBERSHIP_CHANGE_SUBJECT),
    'template': 'im/projects/project_membership_change_notification.txt',
}

MEM_ENROLL_NOTIF = {
    'subject':   _(messages.PROJECT_MEMBERSHIP_ENROLL_SUBJECT),
    'template': 'im/projects/project_membership_enroll_notification.txt',
}

SENDER = settings.SERVER_EMAIL


def membership_change_notify(project, user, action):
    try:
        notification = build_notification(
            SENDER,
            [user.email],
            MEM_CHANGE_NOTIF['subject'] % project.__dict__,
            template=MEM_CHANGE_NOTIF['template'],
            dictionary={'object': project, 'action': action})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)


def membership_enroll_notify(project, user):
    try:
        notification = build_notification(
            SENDER,
            [user.email],
            MEM_ENROLL_NOTIF['subject'] % project.__dict__,
            template=MEM_ENROLL_NOTIF['template'],
            dictionary={'object': project})
        notification.send()
    except NotificationError, e:
        logger.error(e.message)


MEMBERSHIP_REQUEST_DATA = {
    "join": lambda p: (
        _(messages.PROJECT_MEMBERSHIP_REQUEST_SUBJECT) % p.__dict__,
        "im/projects/project_membership_request_notification.txt"),
    "leave": lambda p: (
        _(messages.PROJECT_MEMBERSHIP_LEAVE_REQUEST_SUBJECT) % p.__dict__,
        "im/projects/project_membership_leave_request_notification.txt"),
}


def membership_request_notify(project, requested_user, action):
    owner = project.owner
    if owner is None:
        return
    subject, template = MEMBERSHIP_REQUEST_DATA[action](project)
    try:
        build_notification(
            SENDER, [owner.email], subject,
            template=template,
            dictionary={'object': project, 'user': requested_user.email}
        ).send()
    except NotificationError, e:
        logger.error(e.message)


APPLICATION_DATA = {
    "submit_new": lambda a: (
        [e[1] for e in settings.PROJECT_CREATION_RECIPIENTS],
        _(messages.PROJECT_CREATION_SUBJECT) % a.chain.realname,
        "im/projects/project_creation_notification.txt"),
    "submit_modification": lambda a: (
        [e[1] for e in settings.PROJECT_MODIFICATION_RECIPIENTS],
        _(messages.PROJECT_MODIFICATION_SUBJECT) % a.chain.realname,
        "im/projects/project_modification_notification.txt"),
    "deny": lambda a: (
        [a.applicant.email],
        _(messages.PROJECT_DENIED_SUBJECT) % a.chain.realname,
        "im/projects/project_denial_notification.txt"),
    "approve": lambda a: (
        [a.applicant.email],
        _(messages.PROJECT_APPROVED_SUBJECT) % a.chain.realname,
        "im/projects/project_approval_notification.txt"),
}


def application_notify(application, action):
    recipients, subject, template = APPLICATION_DATA[action](application)
    try:
        build_notification(
            SENDER, recipients, subject,
            template=template,
            dictionary={'object': application}
        ).send()
    except NotificationError, e:
        logger.error(e.message)


PROJECT_DATA = {
    "terminate": lambda p: (
        _(messages.PROJECT_TERMINATION_SUBJECT) % p.realname,
        "im/projects/project_termination_notification.txt"),
    "reinstate": lambda p: (
        _(messages.PROJECT_REINSTATEMENT_SUBJECT) % p.realname,
        "im/projects/project_reinstatement_notification.txt"),
    "suspend": lambda p: (
        _(messages.PROJECT_SUSPENSION_SUBJECT) % p.realname,
        "im/projects/project_suspension_notification.txt"),
    "unsuspend": lambda p: (
        _(messages.PROJECT_UNSUSPENSION_SUBJECT) % p.realname,
        "im/projects/project_unsuspension_notification.txt"),
}


def project_notify(project, action):
    owner = project.owner
    if owner is None:
        return
    subject, template = PROJECT_DATA[action](project)
    try:
        build_notification(
            SENDER, [owner.email], subject,
            template=template,
            dictionary={'object': project}
        ).send()
    except NotificationError, e:
        logger.error(e.message)

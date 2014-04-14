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
import socket

from smtplib import SMTPException

from django.core.mail import send_mail, get_connection
from django.utils.translation import ugettext as _
from synnefo_branding.utils import render_to_string

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


def build_notification(sender, recipients, subject, message=None,
                       template=None, dictionary=None):
    return EmailNotification(
        sender, recipients, subject, message, template, dictionary)


class Notification(object):
    def __init__(self, sender, recipients, subject,
                 message=None, template=None, dictionary=None):
        if not message and not template:
            raise IOError('message and template cannot be both None.')
        dictionary = dictionary or {}
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        self.message = message or render_to_string(template, dictionary)

    def send(self):
        pass


class EmailNotification(Notification):
    def send(self):
        try:
            send_mail(
                self.subject,
                self.message,
                self.sender,
                self.recipients,
                connection=get_connection())
        except (SMTPException, socket.error), e:
            logger.exception(e)
            raise NotificationError(self)


class NotificationError(Exception):
    def __init__(self, nofication):
        self.message = (_(astakos_messages.DETAILED_NOTIFICATION_SEND_ERR) %
                        nofication.__dict__)
        super(NotificationError, self).__init__()

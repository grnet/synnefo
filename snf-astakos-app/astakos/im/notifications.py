# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)

def build_notification(
    sender, recipients, subject, message=None, template=None, dictionary=None):
    return EmailNotification(
        sender, recipients, subject, message, template, dictionary)

class Notification(object):
    def __init__(
        self, sender, recipients, subject,
        message=None, template=None, dictionary=None):
        if not message and not template:
            raise InputError('message and template cannot be both None.')
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
                self.recipients)
        except (SMTPException, socket.error), e:
            logger.exception(e)
            raise NotificationError()

class NotificationError(Exception):
    def __init__(self):
        self.message = _(astakos_messages.DETAILED_NOTIFICATION_SEND_ERR) % self.__dict__
        super(NotificationError, self).__init__()
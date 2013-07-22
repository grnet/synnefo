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

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

from django.core import mail
from django.views import debug

import re

HIDDEN_ALL = settings.HIDDEN_COOKIES + settings.HIDDEN_HEADERS


def mail_admins_safe(subject, message, fail_silently=False, connection=None):
    '''
    Wrapper function to cleanse email body from sensitive content before
    sending it
    '''
    new_msg = ""

    if len(message) > settings.MAIL_MAX_LEN:
        new_msg += "Mail size over limit (truncated)\n\n"
        message = message[:settings.MAIL_MAX_LEN]

    for line in message.splitlines():
        # Lines of interest in the mail are in the form of
        # key:value.
        try:
            (key, value) = line.split(':', 1)
        except ValueError:
            new_msg += line + '\n'
            continue

        new_msg += key + ':'

        # Special case when the first header / cookie printed
        # (prefixed by 'META:{' or 'COOKIES:{') needs to be hidden.
        if value.startswith('{'):
            try:
                (newkey, newval) = value.split(':', 1)
            except ValueError:
                new_msg += value + '\n'
                continue

            new_msg += newkey + ':'
            key = newkey.lstrip('{')
            value = newval

        if key.strip(" '") not in HIDDEN_ALL:
            new_msg += value + '\n'
            continue

        # Append value[-1] to the clensed string, so that commas / closing
        # brackets are printed correctly.
        # (it will 'eat up' the closing bracket if the header is the last one
        # printed)
        new_msg += ' ' + '*'*8 + value[-1] + '\n'

    return mail.mail_admins_plain(subject, new_msg, fail_silently, connection)


class CleanseSettingsMiddleware(object):
    '''
    Prevent django from printing sensitive information (paswords, tokens
    etc), when handling server errors (for both DEBUG and no-DEBUG
    deployments.
    '''
    def __init__(self):
        debug.HIDDEN_SETTINGS = re.compile(settings.HIDDEN_SETTINGS)

        if not hasattr(mail, 'mail_admins_plain'):
            mail.mail_admins_plain = mail.mail_admins
            mail.mail_admins = mail_admins_safe

        raise MiddlewareNotUsed('cleanse settings')

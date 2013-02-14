# Copyright 2013 GRNET S.A. All rights reserved.
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

from synnefo.lib.db.xctx import TransactionContext
from astakos.im.retry_xctx import RetryTransactionHandler
from astakos.im.notifications import Notification

# USAGE
# =====
# @notification_transaction_context(notify=False)
# def a_view(args, ctx=None):
#     ...
#     if ctx:
#         ctx.mark_rollback()
#     ...
#     return http response
#
# OR (more cleanly)
#
# def a_view(args):
#     with notification_transaction_context(notify=False) as ctx:
#         ...
#         ctx.mark_rollback()
#         ...
#         return http response

def notification_transaction_context(**kwargs):
    return RetryTransactionHandler(ctx=NotificationTransactionContext, **kwargs)


class NotificationTransactionContext(TransactionContext):
    def __init__(self, notify=True, **kwargs):
        self._notifications = []
        self._messages      = []
        self._notify        = notify
        TransactionContext.__init__(self, **kwargs)

    def register(self, o):
        if isinstance(o, dict):
            msg = o.get('msg', None)
            if msg is not None:
                if isinstance(msg, basestring):
                    self.queue_message(msg)

            notif = o.get('notif', None)
            if notif is not None:
                if isinstance(notif, Notification):
                    self.queue_notification(notif)

            if o.has_key('value'):
                return o['value']
        return o

    def queue_message(self, m):
        self._messages.append(m)

    def queue_notification(self, n):
        self._notifications.append(n)

    def _send_notifications(self):
        if self._notifications is None:
            return
        # send mail

    def postprocess(self):
        if self._notify:
            self._send_notifications()
        TransactionContext.postprocess(self)

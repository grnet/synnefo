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

from astakos.im.retry_xctx import RetryTransactionHandler
from astakos.im.notification_xctx import NotificationTransactionContext
from astakos.im.models import sync_projects
from astakos.im.project_error import project_error_view

# USAGE
# =====
# @project_transaction_context(sync=True)
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
#     with project_transaction_context(sync=True) as ctx:
#         ...
#         ctx.mark_rollback()
#         ...
#         return http response

def project_transaction_context(**kwargs):
    return RetryTransactionHandler(ctx=ProjectTransactionContext,
                                   on_fail=project_error_view,
                                   **kwargs)

def cmd_project_transaction_context(**kwargs):
    return RetryTransactionHandler(ctx=ProjectTransactionContext,
                                   **kwargs)

class ProjectTransactionContext(NotificationTransactionContext):
    def __init__(self, sync=False, **kwargs):
        self._sync = sync
        NotificationTransactionContext.__init__(self, **kwargs)

    def postprocess(self):
        if self._sync:
            sync_projects()
        NotificationTransactionContext.postprocess(self)

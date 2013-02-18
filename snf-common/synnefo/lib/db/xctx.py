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

from django.db import transaction

# USAGE
# =====
# @transaction_context()
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
#     with transaction_context() as ctx:
#         ...
#         ctx.mark_rollback()
#         ...
#         return http response

def transaction_context(**kwargs):
    return TransactionHandler(ctx=TransactionContext, **kwargs)


class TransactionContext(object):
    def __init__(self, **kwargs):
        self._rollback = False

    def mark_rollback(self):
        self._rollback = True

    def is_marked_rollback(self):
        return self._rollback

    def postprocess(self):
        pass


class TransactionHandler(object):
    def __init__(self, ctx=None, allow_postprocess=True, using=None, **kwargs):
        self.using             = using
        self.db                = (using if using is not None
                                  else transaction.DEFAULT_DB_ALIAS)
        self.ctx_class         = ctx
        self.ctx_kwargs        = kwargs
        self.allow_postprocess = allow_postprocess

    def __call__(self, func):
        def wrap(*args, **kwargs):
            with self as ctx:
                kwargs['ctx'] = ctx
                return func(*args, **kwargs)
        return wrap

    def __enter__(self):
        db = self.db
        transaction.enter_transaction_management(using=db)
        transaction.managed(True, using=db)
        self.ctx = self.ctx_class(self.ctx_kwargs)
        return self.ctx

    def __exit__(self, type, value, traceback):
        db = self.db
        trigger_postprocess = False
        try:
            if value is not None: # exception
                if transaction.is_dirty(using=db) or True:
                    # Rollback, even if is not dirty.
                    # This is a temporary bug fix for
                    # https://code.djangoproject.com/ticket/9964 .
                    # Django prior to 1.3 does not set a transaction
                    # dirty when the DB throws an exception, and thus
                    # does not trigger rollback, resulting in a
                    # dangling aborted DB transaction.
                    transaction.rollback(using=db)
            else:
                if transaction.is_dirty(using=db):
                    if self.ctx.is_marked_rollback():
                        transaction.rollback(using=db)
                    else:
                        try:
                            transaction.commit(using=db)
                        except:
                            transaction.rollback(using=db)
                            raise
                        else:
                            trigger_postprocess = True

                # postprocess,
                # even if there was nothing to commit
                # as long as it's not marked for rollback
                elif not self.ctx.is_marked_rollback():
                    trigger_postprocess = True
        finally:
            transaction.leave_transaction_management(using=db)

            # checking allow_postprocess is needed
            # in order to avoid endless recursion
            if trigger_postprocess and self.allow_postprocess:
                with TransactionHandler(ctx=self.ctx_class,
                                        allow_postprocess=False,
                                        using=self.using,
                                        **self.ctx_kwargs):
                    self.ctx.postprocess()

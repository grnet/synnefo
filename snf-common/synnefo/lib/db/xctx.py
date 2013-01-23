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
# OR
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
    def __init__(self, notify=True):
        self._rollback = False

    def mark_rollback(self):
        self._rollback = True

    def is_marked_rollback(self):
        return self._rollback

    def postprocess(self):
        pass

class TransactionHandler(object):

    def __init__(self, ctx=None, using=None, **kwargs):
        self.db        = (using if using is not None
                          else transaction.DEFAULT_DB_ALIAS)
        self.ctx_class  = ctx
        self.ctx_kwargs = kwargs

    def __call__(self, func):
        def wrap(*args, **kwargs):
            ctx = self.__enter__()
            kwargs['ctx'] = ctx
            typ = value = trace = None
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                typ = type(e)
                value = e
                trace = None
            finally:
                silent = self.__exit__(typ, value, trace)
                if not silent and value:
                    raise value
            return result
        return wrap

    def __enter__(self):
        db = self.db
        transaction.enter_transaction_management(using=db)
        transaction.managed(True, using=db)
        self.ctx = self.ctx_class(self.ctx_kwargs)
        return self.ctx

    def __exit__(self, type, value, traceback):
        db = self.db
        try:
            if value is not None: # exception
                if transaction.is_dirty(using=db):
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
                            self.ctx.postprocess()
        finally:
            transaction.leave_transaction_management(using=db)

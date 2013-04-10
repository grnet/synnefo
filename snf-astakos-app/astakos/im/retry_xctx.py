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

from synnefo.lib.db.xctx import TransactionHandler
from time import sleep

import logging
logger = logging.getLogger(__name__)

class RetryException(Exception):
    pass

class RetryTransactionHandler(TransactionHandler):
    def __init__(self, retries=3, retry_wait=1.0, on_fail=None, **kwargs):
        self.retries    = retries
        self.retry_wait = retry_wait
        self.on_fail    = on_fail
        TransactionHandler.__init__(self, **kwargs)

    def __call__(self, func):
        def wrap(*args, **kwargs):
            while True:
                try:
                    f = TransactionHandler.__call__(self, func)
                    return f(*args, **kwargs)
                except RetryException as e:
                    self.retries -= 1
                    if self.retries <= 0:
                        logger.exception(e)
                        f = self.on_fail
                        if not callable(f):
                            raise
                        return f(*args, **kwargs)
                    sleep(self.retry_wait)
                except BaseException as e:
                    logger.exception(e)
                    f = self.on_fail
                    if not callable(f):
                        raise
                    return f(*args, **kwargs)
        return wrap

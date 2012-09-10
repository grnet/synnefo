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

from functools import wraps
from urlparse import urlparse

from astakos.im.settings import QUEUE_CONNECTION

if QUEUE_CONNECTION:
    from synnefo.lib.queue import (exchange_connect, exchange_send,
                                   exchange_close, UserEvent, Receipt
                                   )

QUEUE_CLIENT_ID = '3'  # Astakos.
INSTANCE_ID = '1'
RESOURCE = 'addcredits'
DEFAULT_CREDITS = 1000

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )
logger = logging.getLogger('endpoint.aquarium')


def wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not QUEUE_CONNECTION:
            return

        try:
            body, key = func(*args, **kwargs)
            conn = exchange_connect(QUEUE_CONNECTION)
            parts = urlparse(QUEUE_CONNECTION)
            exchange = parts.path[1:]
            routing_key = key % exchange
            exchange_send(conn, routing_key, body)
            exchange_close(conn)
        except BaseException, e:
            logger.exception(e)
    return wrapper


@wrapper
def report_user_event(user, create=False):
    eventType = 'create' if not create else 'modify'
    body = UserEvent(QUEUE_CLIENT_ID, user.email, user.is_active, eventType, {}
                     ).format()
    routing_key = '%s.user'
    return body, routing_key


@wrapper
def report_user_credits_event(user):
    body = Receipt(QUEUE_CLIENT_ID, user.email, INSTANCE_ID, RESOURCE,
                   DEFAULT_CREDITS, details={}
                   ).format()
    routing_key = '%s.resource'
    return body, routing_key


def report_credits_event():
    # better approach?
    from astakos.im.models import AstakosUser
    map(report_user_credits_event, AstakosUser.objects.all())

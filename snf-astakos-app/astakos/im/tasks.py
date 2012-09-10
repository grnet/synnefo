# Copyright 2011 GRNET S.A. All rights reserved.
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

from celery.task import task, periodic_task
from celery.schedules import crontab

from functools import wraps

from astakos.im.endpoints.quotaholder import send_quota
from astakos.im.endpoints.aquarium.producer import (report_credits_event,
                                                    report_user_event
                                                    )
from astakos.im.endpoints.aquarium.client import AquariumClient

import logging

logger = logging.getLogger(__name__)


def log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info('Starting the %s with args=%s kwargs=%s' % (
                    func, args, kwargs
                    )
                    )
        return func(*args, **kwargs)
    return wrapper


@periodic_task(run_every=crontab(day_of_month='1'))
@log
def propagate_credits_update():
    report_credits_event()


@task
@log
def propagate_groupmembers_quota(group):
    if group.is_disabled:
        return
    send_quota(group.approved_members)


@task
@log
def request_billing(user, start, end):
    return AquariumClient().get_billing(user, start, end)

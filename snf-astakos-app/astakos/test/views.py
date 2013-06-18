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

from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied
from astakos.im.models import AstakosUser, ProjectApplication
from astakos.im.functions import (join_project, leave_project,
                                  submit_application, approve_application,
                                  get_user_by_id, check_pending_app_quota)
from snf_django.lib.db.transaction import commit_on_success_strict


@commit_on_success_strict()
def join(proj_id, user_id):
    join_project(proj_id, get_user_by_id(user_id))


@commit_on_success_strict()
def leave(proj_id, user_id):
    leave_project(proj_id, get_user_by_id(user_id))


@commit_on_success_strict()
def submit(name, user_id, prec):
    try:
        owner = AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        raise AttributeError('user does not exist')

    precursor = (ProjectApplication.objects.get(id=prec)
                 if prec is not None
                 else None)

    ok, limit = check_pending_app_quota(owner, precursor=precursor)
    if not ok:
        raise PermissionDenied('Limit %s reached', limit)

    resource_policies = [('cyclades.network.private', 5)]
    data = {'owner': owner,
            'name': name,
            'precursor_id': prec,
            'end_date': datetime.now() + timedelta(days=1),
            'member_join_policy': 1,
            'member_leave_policy': 1,
            'resource_policies': resource_policies,
            'request_user': owner
            }

    app = submit_application(**data)
    return app.id


@commit_on_success_strict()
def approve(app_id):
    approve_application(app_id)

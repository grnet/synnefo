# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, timedelta

from astakos.im import transaction
from astakos.im.models import AstakosUser, Project
from astakos.im.functions import (join_project, leave_project,
                                  submit_application, approve_application,
                                  check_pending_app_quota,
                                  ProjectForbidden)


@transaction.commit_on_success
def join(proj_id, user):
    return join_project(proj_id, user)


@transaction.commit_on_success
def leave(memb_id, request_user):
    return leave_project(memb_id, request_user)


@transaction.commit_on_success
def submit(name, user_id, project_id=None):
    try:
        owner = AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        raise AttributeError('user does not exist')

    project = (Project.objects.get(id=project_id) if project_id is not None
               else None)
    ok, limit = check_pending_app_quota(owner, project=project)
    if not ok:
        raise ProjectForbidden('Limit %s reached', limit)

    resource_policies = {'cyclades.network.private': {'member_capacity': 5,
                                                      'project_capacity': 10}}
    data = {'owner': owner,
            'name': name,
            'project_id': project_id,
            'end_date': datetime.now() + timedelta(days=1),
            'member_join_policy': 1,
            'member_leave_policy': 1,
            'resources': resource_policies,
            'request_user': owner
            }

    app = submit_application(**data)
    return app.id, app.chain_id


@transaction.commit_on_success
def approve(app_id):
    approve_application(app_id)

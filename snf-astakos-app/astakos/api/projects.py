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

import re
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q

from snf_django.lib.db.transaction import commit_on_success_strict
from astakos.api.util import json_response

from snf_django.lib import api
from snf_django.lib.api import faults
from .util import user_from_token, invert_dict, read_json_body

from astakos.im import functions
from astakos.im.models import (
    AstakosUser, Project, ProjectApplication, ProjectMembership,
    ProjectResourceGrant, ProjectLog, ProjectMembershipLog)
import synnefo.util.date as date_util


MEMBERSHIP_POLICY_SHOW = {
    functions.AUTO_ACCEPT_POLICY: "auto",
    functions.MODERATED_POLICY:   "moderated",
    functions.CLOSED_POLICY:      "closed",
}

MEMBERSHIP_POLICY = invert_dict(MEMBERSHIP_POLICY_SHOW)

APPLICATION_STATE_SHOW = {
    ProjectApplication.PENDING:   "pending",
    ProjectApplication.APPROVED:  "approved",
    ProjectApplication.REPLACED:  "replaced",
    ProjectApplication.DENIED:    "denied",
    ProjectApplication.DISMISSED: "dismissed",
    ProjectApplication.CANCELLED: "cancelled",
}

PROJECT_STATE_SHOW = {
    Project.O_PENDING:    "pending",
    Project.O_ACTIVE:     "active",
    Project.O_DENIED:     "denied",
    Project.O_DISMISSED:  "dismissed",
    Project.O_CANCELLED:  "cancelled",
    Project.O_SUSPENDED:  "suspended",
    Project.O_TERMINATED: "terminated",
}

PROJECT_STATE = invert_dict(PROJECT_STATE_SHOW)

MEMBERSHIP_STATE_SHOW = {
    ProjectMembership.REQUESTED:       "requested",
    ProjectMembership.ACCEPTED:        "accepted",
    ProjectMembership.LEAVE_REQUESTED: "leave_requested",
    ProjectMembership.USER_SUSPENDED:  "suspended",
    ProjectMembership.REJECTED:        "rejected",
    ProjectMembership.CANCELLED:       "cancelled",
    ProjectMembership.REMOVED:         "removed",
}


def _application_details(application, all_grants):
    grants = all_grants.get(application.id, [])
    resources = {}
    for grant in grants:
        resources[grant.resource.name] = {
            "member_capacity": grant.member_capacity,
            "project_capacity": grant.project_capacity,
        }

    join_policy = MEMBERSHIP_POLICY_SHOW[application.member_join_policy]
    leave_policy = MEMBERSHIP_POLICY_SHOW[application.member_leave_policy]

    d = {
        "name": application.name,
        "owner": application.owner.uuid,
        "applicant": application.applicant.uuid,
        "homepage": application.homepage,
        "description": application.description,
        "start_date": application.start_date,
        "end_date": application.end_date,
        "join_policy": join_policy,
        "leave_policy": leave_policy,
        "max_members": application.limit_on_members_number,
        "resources": resources,
    }
    return d


def get_applications_details(applications):
    grants = ProjectResourceGrant.objects.grants_per_app(applications)

    l = []
    for application in applications:
        d = {
            "id": application.id,
            "project": application.chain_id,
            "state": APPLICATION_STATE_SHOW[application.state],
            "comments": application.comments,
        }
        d.update(_application_details(application, grants))
        l.append(d)
    return l


def get_application_details(application):
    return get_applications_details([application])[0]


def get_projects_details(projects, request_user=None):
    pendings = ProjectApplication.objects.pending_per_project(projects)
    applications = [p.application for p in projects]
    grants = ProjectResourceGrant.objects.grants_per_app(applications)
    deactivations = ProjectLog.objects.last_deactivations(projects)

    l = []
    for project in projects:
        application = project.application
        d = {
            "id": project.id,
            "application": application.id,
            "state": PROJECT_STATE_SHOW[project.overall_state()],
            "creation_date": project.creation_date,
        }
        check = functions.project_check_allowed
        if check(project, request_user,
                 level=functions.APPLICANT_LEVEL, silent=True):
            d["comments"] = application.comments
            pending = pendings.get(project.id)
            d["pending_application"] = pending.id if pending else None
            deact = deactivations.get(project.id)
            if deact is not None:
                d["deactivation_date"] = deact.date
        d.update(_application_details(application, grants))
        l.append(d)
    return l


def get_project_details(project, request_user=None):
    return get_projects_details([project], request_user=request_user)[0]


def get_memberships_details(memberships, request_user):
    all_logs = ProjectMembershipLog.objects.last_logs(memberships)

    l = []
    for membership in memberships:
        logs = all_logs.get(membership.id, {})
        dates = {}
        for s, log in logs.iteritems():
            dates[MEMBERSHIP_STATE_SHOW[s]] = log.date

        allowed_actions = functions.membership_allowed_actions(
            membership, request_user)
        d = {
            "id": membership.id,
            "user": membership.person.uuid,
            "project": membership.project_id,
            "state": MEMBERSHIP_STATE_SHOW[membership.state],
            "allowed_actions": allowed_actions,
        }
        d.update(dates)
        l.append(d)
    return l


def get_membership_details(membership, request_user):
    return get_memberships_details([membership], request_user)[0]


def _query(attr):
    def inner(val):
        kw = attr + "__in" if isinstance(val, list) else attr
        return Q(**{kw: val})
    return inner


def _get_project_state(val):
    try:
        return PROJECT_STATE[val]
    except KeyError:
        raise faults.BadRequest("Unrecognized state %s" % val)


def _project_state_query(val):
    if isinstance(val, list):
        states = [_get_project_state(v) for v in val]
        return Project.o_states_q(states)
    return Project.o_state_q(_get_project_state(val))


PROJECT_QUERY = {
    "name": _query("application__name"),
    "owner": _query("application__owner__uuid"),
    "state": _project_state_query,
}


def make_project_query(filters):
    qs = Q()
    for attr, val in filters.iteritems():
        try:
            _q = PROJECT_QUERY[attr]
        except KeyError:
            raise faults.BadRequest("Unrecognized filter %s" % attr)
        qs &= _q(val)
    return qs


class ExceptionHandler(object):
    def __enter__(self):
        pass

    EXCS = {
        functions.ProjectNotFound:   faults.ItemNotFound,
        functions.ProjectForbidden:  faults.Forbidden,
        functions.ProjectBadRequest: faults.BadRequest,
        functions.ProjectConflict:   faults.Conflict,
    }

    def __exit__(self, exc_type, value, traceback):
        if value is not None:  # exception
            try:
                e = self.EXCS[exc_type]
            except KeyError:
                return False  # reraise
            raise e(value.message)


@csrf_exempt
def projects(request):
    method = request.method
    if method == "GET":
        return get_projects(request)
    elif method == "POST":
        return create_project(request)
    return api.api_method_not_allowed(request)


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def get_projects(request):
    user = request.user
    input_data = read_json_body(request, default={})
    filters = input_data.get("filter", {})
    query = make_project_query(filters)
    projects = _get_projects(query, request_user=user)
    data = get_projects_details(projects, request_user=user)
    return json_response(data)


def _get_projects(query, request_user=None):
    projects = Project.objects.filter(query)

    if not request_user.is_project_admin():
        membs = request_user.projectmembership_set.any_accepted()
        memb_projects = membs.values_list("project", flat=True)
        is_memb = Q(id__in=memb_projects)
        owned = (Q(application__owner=request_user) |
                 Q(application__applicant=request_user))
        active = Project.o_state_q(Project.O_ACTIVE)
        projects = projects.filter(is_memb | owned | active)
    return projects.select_related(
        "application", "application__owner", "application__applicant")


@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def create_project(request):
    user = request.user
    data = request.raw_post_data
    app_data = json.loads(data)
    return submit_application(app_data, user, project_id=None)


@csrf_exempt
def project(request, project_id):
    method = request.method
    if method == "GET":
        return get_project(request, project_id)
    if method == "POST":
        return modify_project(request, project_id)
    return api.api_method_not_allowed(request)


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def get_project(request, project_id):
    user = request.user
    with ExceptionHandler():
        project = _get_project(project_id, request_user=user)
    data = get_project_details(project, user)
    return json_response(data)


def _get_project(project_id, request_user=None):
    project = functions.get_project_by_id(project_id)
    functions.project_check_allowed(
        project, request_user, level=functions.ANY_LEVEL)
    return project


@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def modify_project(request, project_id):
    user = request.user
    data = request.raw_post_data
    app_data = json.loads(data)
    return submit_application(app_data, user, project_id=project_id)


def _get_date(d, key):
    date_str = d.get(key)
    if date_str is not None:
        try:
            return date_util.isoparse(date_str)
        except:
            raise faults.BadRequest("Invalid %s" % key)
    else:
        return None


def _get_maybe_string(d, key):
    value = d.get(key)
    if value is not None and not isinstance(value, basestring):
        raise faults.BadRequest("%s must be string" % key)
    return value


DOMAIN_VALUE_REGEX = re.compile(
    r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$',
    re.IGNORECASE)


def valid_project_name(name):
    return DOMAIN_VALUE_REGEX.match(name) is not None


def submit_application(app_data, user, project_id=None):
    uuid = app_data.get("owner")
    if uuid is None:
        owner = user
    else:
        try:
            owner = AstakosUser.objects.get(uuid=uuid, email_verified=True)
        except AstakosUser.DoesNotExist:
            raise faults.BadRequest("User does not exist.")

    try:
        name = app_data["name"]
    except KeyError:
        raise faults.BadRequest("Name missing.")

    if not valid_project_name(name):
        raise faults.BadRequest("Project name should be in domain format")

    join_policy = app_data.get("join_policy", "moderated")
    try:
        join_policy = MEMBERSHIP_POLICY[join_policy]
    except KeyError:
        raise faults.BadRequest("Invalid join policy")

    leave_policy = app_data.get("leave_policy", "auto")
    try:
        leave_policy = MEMBERSHIP_POLICY[leave_policy]
    except KeyError:
        raise faults.BadRequest("Invalid leave policy")

    start_date = _get_date(app_data, "start_date")
    end_date = _get_date(app_data, "end_date")

    if end_date is None:
        raise faults.BadRequest("Missing end date")

    max_members = app_data.get("max_members")
    if max_members is not None and \
            (not isinstance(max_members, (int, long)) or max_members < 0):
        raise faults.BadRequest("Invalid max_members")

    homepage = _get_maybe_string(app_data, "homepage")
    description = _get_maybe_string(app_data, "description")
    comments = _get_maybe_string(app_data, "comments")
    resources = app_data.get("resources", {})

    submit = functions.submit_application
    with ExceptionHandler():
        application = submit(
            owner=owner,
            name=name,
            project_id=project_id,
            homepage=homepage,
            description=description,
            start_date=start_date,
            end_date=end_date,
            member_join_policy=join_policy,
            member_leave_policy=leave_policy,
            limit_on_members_number=max_members,
            comments=comments,
            resources=resources,
            request_user=user)

    result = {"application": application.id,
              "id": application.chain_id
              }
    return json_response(result, status_code=201)


def get_action(actions, input_data):
    action = None
    data = None
    for option in actions.keys():
        if option in input_data:
            if action:
                raise faults.BadRequest("Multiple actions not supported")
            else:
                action = option
                data = input_data[action]
    if not action:
        raise faults.BadRequest("No recognized action")
    return actions[action], data


PROJECT_ACTION = {
    "terminate": functions.terminate,
    "suspend":   functions.suspend,
    "unsuspend": functions.unsuspend,
    "reinstate": functions.reinstate,
}


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def project_action(request, project_id):
    user = request.user
    data = request.raw_post_data
    input_data = json.loads(data)

    func, action_data = get_action(PROJECT_ACTION, input_data)
    with ExceptionHandler():
        func(project_id, request_user=user, reason=action_data)
    return HttpResponse()


@csrf_exempt
def applications(request):
    method = request.method
    if method == "GET":
        return get_applications(request)
    return api.api_method_not_allowed(request)


def make_application_query(input_data):
    project_id = input_data.get("project")
    if project_id is not None:
        if not isinstance(project_id, (int, long)):
            raise faults.BadRequest("'project' must be integer")
        return Q(chain=project_id)
    return Q()


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def get_applications(request):
    user = request.user
    input_data = read_json_body(request, default={})
    query = make_application_query(input_data)
    apps = _get_applications(query, request_user=user)
    data = get_applications_details(apps)
    return json_response(data)


def _get_applications(query, request_user=None):
    apps = ProjectApplication.objects.filter(query)

    if not request_user.is_project_admin():
        owned = (Q(owner=request_user) |
                 Q(applicant=request_user))
        apps = apps.filter(owned)
    return apps.select_related()


@csrf_exempt
@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def application(request, app_id):
    user = request.user
    with ExceptionHandler():
        application = _get_application(app_id, user)
    data = get_application_details(application)
    return json_response(data)


def _get_application(app_id, request_user=None):
    application = functions.get_application(app_id)
    functions.app_check_allowed(
        application, request_user, level=functions.APPLICANT_LEVEL)
    return application


APPLICATION_ACTION = {
    "approve": functions.approve_application,
    "deny": functions.deny_application,
    "dismiss": functions.dismiss_application,
    "cancel": functions.cancel_application,
}


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def application_action(request, app_id):
    user = request.user
    data = request.raw_post_data
    input_data = json.loads(data)

    func, action_data = get_action(APPLICATION_ACTION, input_data)
    with ExceptionHandler():
        func(app_id, request_user=user, reason=action_data)

    return HttpResponse()


@csrf_exempt
def memberships(request):
    method = request.method
    if method == "GET":
        return get_memberships(request)
    elif method == "POST":
        return post_memberships(request)
    return api.api_method_not_allowed(request)


def make_membership_query(input_data):
    project_id = input_data.get("project")
    if project_id is not None:
        if not isinstance(project_id, (int, long)):
            raise faults.BadRequest("'project' must be integer")
        return Q(project=project_id)
    return Q()


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def get_memberships(request):
    user = request.user
    input_data = read_json_body(request, default={})
    query = make_membership_query(input_data)
    memberships = _get_memberships(query, request_user=user)
    data = get_memberships_details(memberships, user)
    return json_response(data)


def _get_memberships(query, request_user=None):
    memberships = ProjectMembership.objects
    if not request_user.is_project_admin():
        owned = Q(project__application__owner=request_user)
        memb = Q(person=request_user)
        memberships = memberships.filter(owned | memb)

    return memberships.select_related(
        "project", "project__application",
        "project__application__owner", "project__application__applicant",
        "person").filter(query)


def join_project(data, request_user):
    project_id = data.get("project")
    with ExceptionHandler():
        membership = functions.join_project(project_id, request_user)
    response = {"id": membership.id}
    return json_response(response)


def enroll_user(data, request_user):
    project_id = data.get("project")
    email = data.get("user")
    with ExceptionHandler():
        m = functions.enroll_member_by_email(
            project_id, email, request_user)

    response = {"id": m.id}
    return json_response(response)


MEMBERSHIPS_ACTION = {
    "join":   join_project,
    "enroll": enroll_user,
}


@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def post_memberships(request):
    user = request.user
    data = request.raw_post_data
    input_data = json.loads(data)
    func, action_data = get_action(MEMBERSHIPS_ACTION, input_data)
    return func(action_data, user)


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def membership(request, memb_id):
    user = request.user
    with ExceptionHandler():
        m = _get_membership(memb_id, request_user=user)
    data = get_membership_details(m, user)
    return json_response(data)


def _get_membership(memb_id, request_user=None):
    membership = functions.get_membership_by_id(memb_id)
    functions.membership_check_allowed(membership, request_user)
    return membership


MEMBERSHIP_ACTION = {
    "leave":  functions.leave_project,
    "cancel": functions.cancel_membership,
    "accept": functions.accept_membership,
    "reject": functions.reject_membership,
    "remove": functions.remove_membership,
}


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@commit_on_success_strict()
def membership_action(request, memb_id):
    user = request.user
    input_data = read_json_body(request, default={})
    func, action_data = get_action(MEMBERSHIP_ACTION, input_data)
    with ExceptionHandler():
        func(memb_id, user, reason=action_data)
    return HttpResponse()

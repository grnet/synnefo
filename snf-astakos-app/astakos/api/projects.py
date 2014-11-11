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

import operator

from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q
from astakos.im import transaction

from astakos.api.util import json_response

from snf_django.lib import api
from snf_django.lib.api import faults
from snf_django.lib.api import utils
from .util import user_from_token, invert_dict, check_is_dict

from astakos.im import functions
from astakos.im.models import (
    AstakosUser, Project, ProjectApplication, ProjectMembership,
    ProjectResourceQuota, ProjectResourceGrant, ProjectLog,
    ProjectMembershipLog)
from synnefo.util import units


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
    Project.UNINITIALIZED: "uninitialized",
    Project.NORMAL:        "active",
    Project.SUSPENDED:     "suspended",
    Project.TERMINATED:    "terminated",
    Project.DELETED:       "deleted",
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


def _grant_details(grants):
    resources = {}
    for grant in grants:
        if not grant.resource.api_visible:
            continue
        resources[grant.resource.name] = {
            "member_capacity": grant.member_capacity,
            "project_capacity": grant.project_capacity,
        }
    return resources


def _application_details(application, all_grants):
    grants = all_grants.get(application.id, [])
    resources = _grant_details(grants)
    join_policy = MEMBERSHIP_POLICY_SHOW.get(application.member_join_policy)
    leave_policy = MEMBERSHIP_POLICY_SHOW.get(application.member_leave_policy)

    d = {
        "id": application.id,
        "state": APPLICATION_STATE_SHOW[application.state],
        "name": application.name,
        "owner": application.owner.uuid if application.owner else None,
        "applicant": application.applicant.uuid,
        "homepage": application.homepage,
        "description": application.description,
        "start_date": application.start_date,
        "end_date": application.end_date,
        "comments": application.comments,
        "join_policy": join_policy,
        "leave_policy": leave_policy,
        "max_members": application.limit_on_members_number,
        "private": application.private,
        "resources": resources,
    }
    return d


def get_projects_details(projects, request_user=None):
    applications = [p.last_application for p in projects if p.last_application]
    proj_quotas = ProjectResourceQuota.objects.quotas_per_project(projects)
    app_grants = ProjectResourceGrant.objects.grants_per_app(applications)
    deactivations = ProjectLog.objects.last_deactivations(projects)

    l = []
    for project in projects:
        join_policy = MEMBERSHIP_POLICY_SHOW[project.member_join_policy]
        leave_policy = MEMBERSHIP_POLICY_SHOW[project.member_leave_policy]
        quotas = proj_quotas.get(project.id, [])
        resources = _grant_details(quotas)

        d = {
            "id": project.uuid,
            "state": PROJECT_STATE_SHOW[project.state],
            "creation_date": project.creation_date,
            "name": project.realname,
            "owner": project.owner.uuid if project.owner else None,
            "homepage": project.homepage,
            "description": project.description,
            "end_date": project.end_date,
            "join_policy": join_policy,
            "leave_policy": leave_policy,
            "max_members": project.limit_on_members_number,
            "private": project.private,
            "system_project": project.is_base,
            "resources": resources,
            }

        check = functions.project_check_allowed
        if check(project, request_user,
                 level=functions.APPLICANT_LEVEL, silent=True):
            application = project.last_application
            if application:
                d["last_application"] = _application_details(
                    application, app_grants)
            deact = deactivations.get(project.id)
            if deact is not None:
                d["deactivation_date"] = deact.date
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
            "project": membership.project.uuid,
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
        return Q(state__in=states)
    return Q(state=_get_project_state(val))


PROJECT_QUERY = {
    "name": _query("realname"),
    "owner": _query("owner__uuid"),
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
    return api.api_method_not_allowed(request, allowed_methods=['GET', 'POST'])


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
def get_projects(request):
    user = request.user
    filters = {}
    for key in PROJECT_QUERY.keys():
        value = request.GET.get(key)
        if value is not None:
            filters[key] = value
    mode = request.GET.get("mode", "default")
    query = make_project_query(filters)
    projects = _get_projects(query, mode=mode, request_user=user)
    data = get_projects_details(projects, request_user=user)
    return json_response(data)


def _get_projects(query, mode="default", request_user=None):
    projects = Project.objects.filter(query)

    filters = [Q()]
    if mode == "member":
        membs = request_user.projectmembership_set.\
            actually_accepted_and_active()
        memb_projects = membs.values_list("project", flat=True)
        is_memb = Q(id__in=memb_projects)
        filters.append(is_memb)
    elif mode in ["related", "default"]:
        membs = request_user.projectmembership_set.any_accepted()
        memb_projects = membs.values_list("project", flat=True)
        is_memb = Q(id__in=memb_projects)
        owned = Q(owner=request_user)
        if not request_user.is_project_admin():
            filters.append(is_memb)
            filters.append(owned)
    elif mode in ["active", "default"]:
        active = (Q(state=Project.NORMAL) & Q(private=False))
        if not request_user.is_project_admin():
            filters.append(active)
    else:
        raise faults.BadRequest("Unrecognized mode '%s'." % mode)

    q = reduce(operator.or_, filters)
    projects = projects.filter(q)
    return projects.select_related("last_application")


@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
def create_project(request):
    user = request.user
    app_data = utils.get_json_body(request)
    return submit_new_project(app_data, user)


@csrf_exempt
def project(request, project_id):
    method = request.method
    if method == "GET":
        return get_project(request, project_id)
    if method == "PUT":
        return modify_project(request, project_id)
    return api.api_method_not_allowed(request, allowed_methods=['GET', 'PUT'])


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
def get_project(request, project_id):
    user = request.user
    with ExceptionHandler():
        project = _get_project(project_id, request_user=user)
    data = get_project_details(project, user)
    return json_response(data)


def _get_project(project_id, request_user=None):
    project = functions.get_project_by_uuid(project_id)
    functions.project_check_allowed(
        project, request_user, level=functions.ANY_LEVEL)
    return project


@api.api_method(http_method="PUT", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
def modify_project(request, project_id):
    user = request.user
    app_data = utils.get_json_body(request)
    return submit_modification(app_data, user, project_id=project_id)


def _get_maybe_string(d, key, default=None):
    value = d.get(key)
    if value is not None and not isinstance(value, basestring):
        raise faults.BadRequest("%s must be string" % key)
    if value is None:
        return default
    return value


def _get_maybe_boolean(d, key, default=None):
    value = d.get(key)
    if value is not None and not isinstance(value, bool):
        raise faults.BadRequest("%s must be boolean" % key)
    if value is None:
        return default
    return value


def _parse_max_members(s):
    try:
        return units.parse(s)
    except units.ParseError:
        raise faults.BadRequest("Invalid max_members")


def submit_new_project(app_data, user):
    uuid = app_data.get("owner")
    if uuid is None:
        owner = user
    else:
        try:
            owner = AstakosUser.objects.accepted().get(uuid=uuid)
        except AstakosUser.DoesNotExist:
            raise faults.BadRequest("User does not exist.")

    try:
        name = app_data["name"]
    except KeyError:
        raise faults.BadRequest("Name missing.")

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

    start_date = app_data.get("start_date")
    end_date = app_data.get("end_date")

    if end_date is None:
        raise faults.BadRequest("Missing end date")

    try:
        max_members = _parse_max_members(app_data["max_members"])
    except KeyError:
        max_members = units.PRACTICALLY_INFINITE

    private = bool(_get_maybe_boolean(app_data, "private"))
    homepage = _get_maybe_string(app_data, "homepage", "")
    description = _get_maybe_string(app_data, "description", "")
    comments = _get_maybe_string(app_data, "comments", "")
    resources = app_data.get("resources", {})

    submit = functions.submit_application
    with ExceptionHandler():
        application = submit(
            owner=owner,
            name=name,
            project_id=None,
            homepage=homepage,
            description=description,
            start_date=start_date,
            end_date=end_date,
            member_join_policy=join_policy,
            member_leave_policy=leave_policy,
            limit_on_members_number=max_members,
            private=private,
            comments=comments,
            resources=resources,
            request_user=user)

    result = {"application": application.id,
              "id": application.chain.uuid,
              }
    return json_response(result, status_code=201)


def submit_modification(app_data, user, project_id):
    owner = app_data.get("owner")
    if owner is not None:
        try:
            owner = AstakosUser.objects.accepted().get(uuid=owner)
        except AstakosUser.DoesNotExist:
            raise faults.BadRequest("User does not exist.")

    name = app_data.get("name")

    join_policy = app_data.get("join_policy")
    if join_policy is not None:
        try:
            join_policy = MEMBERSHIP_POLICY[join_policy]
        except KeyError:
            raise faults.BadRequest("Invalid join policy")

    leave_policy = app_data.get("leave_policy")
    if leave_policy is not None:
        try:
            leave_policy = MEMBERSHIP_POLICY[leave_policy]
        except KeyError:
            raise faults.BadRequest("Invalid leave policy")

    start_date = app_data.get("start_date")
    end_date = app_data.get("end_date")

    max_members = app_data.get("max_members")
    if max_members is not None:
        max_members = _parse_max_members(max_members)

    private = _get_maybe_boolean(app_data, "private")
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
            private=private,
            comments=comments,
            resources=resources,
            request_user=user)

    result = {"application": application.id,
              "id": application.chain.uuid,
              }
    return json_response(result, status_code=201)


def get_action(actions, input_data):
    action = None
    data = None
    check_is_dict(input_data)
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


APPLICATION_ACTION = {
    "approve": functions.approve_application,
    "deny":    functions.deny_application,
    "dismiss": functions.dismiss_application,
    "cancel":  functions.cancel_application,
}


PROJECT_ACTION.update(APPLICATION_ACTION)
APP_ACTION_FUNCS = APPLICATION_ACTION.values()


@csrf_exempt
@api.api_method(http_method="POST", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
def project_action(request, project_id):
    user = request.user
    input_data = utils.get_json_body(request)

    func, action_data = get_action(PROJECT_ACTION, input_data)
    with ExceptionHandler():
        kwargs = {"request_user": user,
                  "reason": action_data.get("reason", ""),
                  }
        if func in APP_ACTION_FUNCS:
            kwargs["application_id"] = action_data["app_id"]
        func(project_id=project_id, **kwargs)
    return HttpResponse()


@csrf_exempt
def memberships(request):
    method = request.method
    if method == "GET":
        return get_memberships(request)
    elif method == "POST":
        return post_memberships(request)
    return api.api_method_not_allowed(request, allowed_methods=['GET', 'POST'])


def make_membership_query(input_data):
    project_id = input_data.get("project")
    if project_id is not None:
        return Q(project__uuid=project_id)
    return Q()


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
def get_memberships(request):
    user = request.user
    query = make_membership_query(request.GET)
    memberships = _get_memberships(query, request_user=user)
    data = get_memberships_details(memberships, user)
    return json_response(data)


def _get_memberships(query, request_user=None):
    memberships = ProjectMembership.objects
    if not request_user.is_project_admin():
        owned = Q(project__owner=request_user)
        memb = Q(person=request_user)
        memberships = memberships.filter(owned | memb)

    return memberships.select_related(
        "project", "project__owner", "person").filter(query)


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
@transaction.commit_on_success
def post_memberships(request):
    user = request.user
    data = request.body
    input_data = json.loads(data)
    func, action_data = get_action(MEMBERSHIPS_ACTION, input_data)
    return func(action_data, user)


@api.api_method(http_method="GET", token_required=True, user_required=False)
@user_from_token
@transaction.commit_on_success
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
@transaction.commit_on_success
def membership_action(request, memb_id):
    user = request.user
    input_data = utils.get_json_body(request)
    func, action_data = get_action(MEMBERSHIP_ACTION, input_data)
    with ExceptionHandler():
        func(memb_id, user, reason=action_data)
    return HttpResponse()

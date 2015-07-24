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

import logging

from functools import wraps
from django_tables2 import RequestConfig

from django.shortcuts import get_object_or_404, render_to_response
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list, object_detail
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from astakos.im import transaction
from django.template import RequestContext
from django.db.models import Q

import astakos.im.messages as astakos_messages

from astakos.im import tables
from astakos.im.models import ProjectApplication, ProjectMembership, Project
from astakos.im.util import get_context, restrict_next, restrict_reverse
from astakos.im.forms import ProjectApplicationForm, AddProjectMembersForm, \
    ProjectSearchForm, ProjectModificationForm
from astakos.im.functions import check_pending_app_quota, accept_membership, \
    reject_membership, remove_membership, cancel_membership, leave_project, \
    join_project, enroll_member, can_join_request, can_leave_request, \
    get_related_project_id, approve_application, \
    deny_application, cancel_application, dismiss_application, ProjectError, \
    can_cancel_join_request, app_check_allowed, project_check_allowed, \
    ProjectForbidden
from astakos.im import settings
from astakos.im.util import redirect_back
from astakos.im.views.util import render_response, _create_object, \
    _update_object, _resources_catalog, ExceptionHandler, \
    get_user_projects_table, handle_valid_members_form, redirect_to_next
from astakos.im.views.decorators import cookie_fix, signed_terms_required,\
    valid_astakos_user_required, login_required

from astakos.api import projects as api
from astakos.im import functions as project_actions

logger = logging.getLogger(__name__)


def no_transaction(func):
    return func


def handles_project_errors(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ProjectForbidden:
            raise PermissionDenied
    return wrapper


def project_view(get=True, post=False, transaction=False):
    methods = []
    if get:
        methods.append("GET")
    if post:
        methods.append("POST")

    if transaction:
        transaction_method = transaction.commit_on_success
    else:
        transaction_method = no_transaction

    def wrapper(func):
        return \
            wraps(func)(
                require_http_methods(methods)(
                    cookie_fix(
                        valid_astakos_user_required(
                            transaction_method(
                                handles_project_errors(func))))))

    return wrapper


@project_view()
def how_it_works(request):
    return render_response('im/how_it_works.html',
                           context_instance=get_context(request))


@project_view()
def project_list(request, template_name="im/projects/project_list.html"):
    query = api.make_project_query({})
    show_base = request.GET.get('show_base', False)

    # exclude base projects by default for admin users
    if not show_base and request.user.is_project_admin():
        query = query & ~Q(Q(is_base=True) & \
                          ~Q(realname="system:%s" % request.user.uuid))

    query = query & ~Q(state__in=Project.HIDDEN_STATES)
    mode = "default"
    if not request.user.is_project_admin():
        mode = "related"

    projects = api._get_projects(query, mode=mode, request_user=request.user)

    table = None
    if projects.count():
        table = get_user_projects_table(projects, user=request.user,
                                        prefix="my_projects_", request=request)

    context = {'is_search': False, 'table': table}
    return object_list(request, projects, template_name=template_name,
                       extra_context=context)


@project_view(post=True)
def project_add_or_modify(request, project_uuid=None):
    user = request.user

    # only check quota for non project admin users
    if not user.is_project_admin():
        ok, limit = check_pending_app_quota(user)
        if not ok:
            m = _(astakos_messages.PENDING_APPLICATION_LIMIT_ADD) % limit
            messages.error(request, m)
            return redirect(restrict_reverse(
                'astakos.im.views.project_list'))

    project = None
    if project_uuid:
        project = get_object_or_404(Project, uuid=project_uuid)

        if not user.owns_project(project) and not user.is_project_admin():
            m = _(astakos_messages.NOT_ALLOWED)
            raise PermissionDenied(m)

    details_fields = ["name", "homepage", "description", "start_date",
                      "end_date", "comments"]
    membership_fields = ["member_join_policy", "member_leave_policy",
                         "limit_on_members_number"]

    resource_catalog, resource_groups = _resources_catalog()
    resource_catalog_dict, resource_groups_dict = \
        _resources_catalog(as_dict=True)

    extra_context = {
        'resource_catalog': resource_catalog,
        'resource_groups': resource_groups,
        'resource_catalog_dict': resource_catalog_dict,
        'resource_groups_dict': resource_groups_dict,
        'show_form': True,
        'details_fields': details_fields,
        'membership_fields': membership_fields,
        'object': project
    }

    with transaction.commit_on_success():
        template_name = 'im/projects/projectapplication_form.html'
        summary_template_name = \
            'im/projects/projectapplication_form_summary.html'
        success_msg = _("The project application has been received and "
                        "is under consideration.")
        form_class = ProjectApplicationForm

        if project:
            template_name = 'im/projects/projectmodification_form.html'
            summary_template_name = \
                'im/projects/projectmodification_form_summary.html'
            success_msg = _("The project modification has been received and "
                            "is under consideration.")
            form_class = ProjectModificationForm
            details_fields.remove('start_date')

        extra_context['edit'] = 0
        if request.method == 'POST':
            form = form_class(request.POST, request.FILES, instance=project)
            if form.is_valid():
                verify = request.GET.get('verify')
                edit = request.GET.get('edit')
                if verify == '1':
                    extra_context['show_form'] = False
                    extra_context['form_data'] = form.cleaned_data
                    template_name = summary_template_name
                elif edit == '1':
                    extra_context['show_form'] = True
                else:
                    new_object = form.save()
                    messages.success(request, success_msg,
                                     fail_silently=True)
                    return redirect(restrict_reverse('project_list'))
        else:
            # handle terminated projects for which the name attribute
            # has been set to null
            if project and not project.name:
                project.name = project.realname
            form = form_class(instance=project)

        extra_context['form'] = form
        return render_to_response(template_name, extra_context,
                                  context_instance=RequestContext(request))


@project_view(get=False, post=True)
def project_app_cancel(request, project_uuid, application_id):
    with ExceptionHandler(request):
        with transaction.commit_on_success():
            cancel_application(application_id, project_uuid,
                               request_user=request.user)
            messages.success(request,
                             _(astakos_messages.APPLICATION_CANCELLED))
    return redirect(reverse('project_list'))


@project_view(post=True)
def project_or_app_detail(request, project_uuid, app_id=None):

    project = get_object_or_404(Project, uuid=project_uuid)
    application = None
    if app_id:
        application = get_object_or_404(ProjectApplication, id=app_id)
        app_check_allowed(application, request.user)
        if request.method == "POST":
            raise PermissionDenied

    if project.state in [Project.O_PENDING] and not application and \
       project.last_application:
        return redirect(reverse('project_app',
                                args=(project.uuid,
                                      project.last_application.id,)))

    members = project.projectmembership_set

    # handle members form submission
    if request.method == 'POST' and not application:
        project_check_allowed(project, request.user)
        addmembers_form = AddProjectMembersForm(
            request.POST,
            project_id=project.pk,
            request_user=request.user)
        with ExceptionHandler(request):
            handle_valid_members_form(request, project.pk, addmembers_form)

        if addmembers_form.is_valid():
            addmembers_form = AddProjectMembersForm()  # clear form data
    else:
        addmembers_form = AddProjectMembersForm()  # initialize form

    approved_members_count = project.members_count()
    pending_members_count = project.count_pending_memberships()
    _limit = project.limit_on_members_number
    remaining_memberships_count = (max(0, _limit - approved_members_count)
                                   if _limit is not None else None)
    members = members.associated()
    members = members.select_related()
    members_table = tables.ProjectMembersTable(project,
                                               members,
                                               user=request.user,
                                               prefix="members_")
    paginate = {"per_page": settings.PAGINATE_BY}
    RequestConfig(request, paginate=paginate).configure(members_table)

    user = request.user
    owns_base = False
    if project and project.is_base and \
                           project.realname == "system:%s" % request.user.uuid:
        owns_base = True
    is_project_admin = user.is_project_admin()
    is_owner = user.owns_project(project)
    is_applicant = False
    last_pending_app = project.last_pending_application()
    if last_pending_app:
        is_applicant = last_pending_app and \
                last_pending_app.applicant.pk == user.pk

    if not (is_owner or is_project_admin) and \
            not user.non_owner_can_view(project):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    if project and project.is_base and not (owns_base or is_project_admin):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    membership = user.get_membership(project) if project else None
    membership_id = membership.id if membership else None
    mem_display = user.membership_display(project) if project else None
    can_join_req = can_join_request(project, user) if project else False
    can_leave_req = can_leave_request(project, user) if project else False
    can_cancel_req = \
            can_cancel_join_request(project, user) if project else False

    is_modification = application.is_modification() if application else False

    queryset = Project.objects.select_related()
    object_id = project.pk
    resources_set = project.resource_set
    template_name = "im/projects/project_detail.html"
    if application:
        queryset = ProjectApplication.objects.select_related()
        object_id = application.pk
        is_applicant = application.applicant.pk == user.pk
        resources_set = application.resource_set
        template_name = "im/projects/project_application_detail.html"

    display_usage = False
    if (owns_base or is_owner or membership or is_project_admin) \
                                                               and not app_id:
        display_usage = True

    return object_detail(
        request,
        queryset=queryset,
        object_id=object_id,
        template_name=template_name,
        extra_context={
            'project': project,
            'application': application,
            'is_application': bool(application),
            'display_usage': display_usage,
            'is_modification': is_modification,
            'addmembers_form': addmembers_form,
            'approved_members_count': approved_members_count,
            'pending_members_count': pending_members_count,
            'members_table': members_table,
            'owner_mode': is_owner,
            'admin_mode': is_project_admin,
            'applicant_mode': is_applicant,
            'mem_display': mem_display,
            'membership_id': membership_id,
            'can_join_request': can_join_req,
            'can_leave_request': can_leave_req,
            'can_cancel_join_request': can_cancel_req,
            'resources_set': resources_set,
            'last_app': None if application else project.last_application,
            'remaining_memberships_count': remaining_memberships_count
        })


MEMBERSHIP_STATUS_FILTER = {
    0: {'state': ProjectMembership.REQUESTED},
    1: {'state__in': ProjectMembership.ACCEPTED_STATES}
}


@require_http_methods(["GET", "POST"])
@cookie_fix
@valid_astakos_user_required
def project_search(request):
    q = request.GET.get('q', '')
    form = ProjectSearchForm()
    q = q.strip()

    if request.method == "POST":
        form = ProjectSearchForm(request.POST)
        if form.is_valid():
            q = form.cleaned_data['q'].strip()
        else:
            q = None

    if q is None:
        projects = Project.objects.none()
    else:
        query = ~Q(state=Project.DELETED)
        projects = api._get_projects(query, mode="active",
                                     request_user=request.user)

    table = get_user_projects_table(projects, user=request.user,
                                    prefix="my_projects_")
    if request.method == "POST":
        table.caption = _('SEARCH RESULTS')
    else:
        table.caption = _('ALL PROJECTS')

    return object_list(
        request,
        projects,
        template_name='im/projects/project_list.html',
        extra_context={
            'form': form,
            'is_search': True,
            'q': q,
            'table': table
        })


@project_view(get=False, post=True)
def project_join(request, project_uuid):
    project = get_object_or_404(Project, uuid=project_uuid)
    with ExceptionHandler(request):
        with transaction.commit_on_success():
            membership = join_project(project_uuid, request.user)
            if membership.state != membership.REQUESTED:
                m = _(astakos_messages.USER_JOINED_PROJECT)
            else:
                m = _(astakos_messages.USER_JOIN_REQUEST_SUBMITTED)
            messages.success(request, m)
    return redirect_to_next(request, 'project_detail', args=(project.uuid,))


@project_view(get=False, post=True)
def project_leave(request, project_uuid):
    project = get_object_or_404(Project, uuid=project_uuid)
    with ExceptionHandler(request):
        with transaction.commit_on_success():
            memb_id = request.user.get_membership(project).pk
            auto_accepted = leave_project(memb_id, request.user)
            if auto_accepted:
                m = _(astakos_messages.USER_LEFT_PROJECT)
            else:
                m = _(astakos_messages.USER_LEAVE_REQUEST_SUBMITTED)
            messages.success(request, m)
    return redirect_to_next(request, 'project_detail', args=(project.uuid,))


@project_view(get=False, post=True)
def project_cancel_join(request, project_uuid):
    project = get_object_or_404(Project, uuid=project_uuid)
    with ExceptionHandler(request):
        with transaction.commit_on_success():
            project = get_object_or_404(Project, uuid=project_uuid)
            memb_id = request.user.get_membership(project).pk
            cancel_membership(memb_id, request.user)
            m = _(astakos_messages.USER_REQUEST_CANCELLED)
            messages.success(request, m)
    return redirect_to_next(request, 'project_detail', args=(project.uuid,))


@project_view(get=False, post=True)
def project_app_approve(request, project_uuid, application_id):
    with ExceptionHandler(request):
        with transaction.commit_on_success():
            approve_application(application_id, project_uuid,
                                request_user=request.user)
            messages.success(request, _(astakos_messages.APPLICATION_APPROVED))
    return redirect(reverse('project_detail', args=(project_uuid,)))


@project_view(get=False, post=True)
def project_app_deny(request, project_uuid, application_id):
    with ExceptionHandler(request):
        reason = request.POST.get("reason", "")
        with transaction.commit_on_success():
            deny_application(application_id, project_uuid,
                             request_user=request.user, reason=reason)
            messages.success(request, _(astakos_messages.APPLICATION_DENIED))
    return redirect(reverse("project_list"))


@project_view(get=False, post=True)
def project_app_dismiss(request, project_uuid, application_id):
    with ExceptionHandler(request):
        with transaction.commit_on_success():
            dismiss_application(application_id, project_uuid,
                                request_user=request.user)
            messages.success(request,
                             _(astakos_messages.APPLICATION_DISMISSED))
    return redirect(reverse("project_list"))


@project_view(post=True)
def project_members(request, project_uuid, members_status_filter=None,
                    template_name='im/projects/project_members.html'):
    project = get_object_or_404(Project, uuid=project_uuid)

    user = request.user
    if not user.owns_project(project) and not user.is_project_admin():
        return redirect(reverse('index'))

    if not project.is_alive:
        return redirect(reverse('project_list'))

    if request.method == 'POST':
        addmembers_form = AddProjectMembersForm(
            request.POST,
            chain_id=int(chain_id),
            request_user=request.user)
        with ExceptionHandler(request):
            handle_valid_members_form(request, chain_id, addmembers_form)

        if addmembers_form.is_valid():
            addmembers_form = AddProjectMembersForm()  # clear form data
    else:
        addmembers_form = AddProjectMembersForm()  # initialize form

    query = api.make_membership_query({'project': project_uuid})
    members = api._get_memberships(query, request_user=user)
    approved_members_count = project.members_count()
    pending_members_count = project.count_pending_memberships()
    _limit = project.limit_on_members_number
    if _limit is not None:
        remaining_memberships_count = \
            max(0, _limit - approved_members_count)
    flt = MEMBERSHIP_STATUS_FILTER.get(members_status_filter)
    if flt is not None:
        members = members.filter(**flt)
    else:
        members = members.filter(state__in=ProjectMembership.ASSOCIATED_STATES)

    members = members.select_related()
    members_table = tables.ProjectMembersTable(project,
                                               members,
                                               user=request.user,
                                               prefix="members_")
    RequestConfig(request, paginate={"per_page": settings.PAGINATE_BY}
                  ).configure(members_table)

    user = request.user
    is_project_admin = user.is_project_admin()
    is_owner = user.owns_application(project)
    if (
        not (is_owner or is_project_admin) and
        not user.non_owner_can_view(project)
    ):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    membership = user.get_membership(project) if project else None
    membership_id = membership.id if membership else None
    mem_display = user.membership_display(project) if project else None
    can_join_req = can_join_request(project, user) if project else False
    can_leave_req = can_leave_request(project, user) if project else False

    return object_detail(
        request,
        queryset=Project.objects.select_related(),
        object_id=project.id,
        template_name='im/projects/project_members.html',
        extra_context={
            'addmembers_form': addmembers_form,
            'approved_members_count': approved_members_count,
            'pending_members_count': pending_members_count,
            'members_table': members_table,
            'owner_mode': is_owner,
            'admin_mode': is_project_admin,
            'mem_display': mem_display,
            'membership_id': membership_id,
            'can_join_request': can_join_req,
            'can_leave_request': can_leave_req,
            'members_status_filter': members_status_filter,
            'project': project,
            'remaining_memberships_count': remaining_memberships_count,
        })


@project_view(get=False, post=True)
def project_members_action(request, project_uuid, action=None, redirect_to='',
                           memb_id=None):

    actions_map = {
        'remove': {
            'method': 'remove_membership',
            'msg': _(astakos_messages.USER_MEMBERSHIP_REMOVED)
        },
        'accept': {
            'method': 'accept_membership',
            'msg': _(astakos_messages.USER_MEMBERSHIP_ACCEPTED)
        },
        'reject': {
            'method': 'reject_membership',
            'msg': _(astakos_messages.USER_MEMBERSHIP_REJECTED)
        }
    }

    if not action in actions_map.keys():
        raise PermissionDenied

    if memb_id:
        member_ids = [memb_id]
    else:
        member_ids = request.POST.getlist('members')

    project = get_object_or_404(Project, uuid=project_uuid)

    user = request.user
    if not user.owns_project(project) and not user.is_project_admin():
        messages.error(request, astakos_messages.NOT_ALLOWED)
        return redirect(reverse('index'))

    logger.info("Member(s) action from %s (project: %r, action: %s, "
                "members: %r)", user.log_display, project.uuid, action,
                member_ids)

    action = actions_map.get(action)
    action_func = getattr(project_actions, action.get('method'))
    for member_id in member_ids:
        member_id = int(member_id)
        with ExceptionHandler(request):
            with transaction.commit_on_success():
                try:
                    m = action_func(member_id, request.user)
                except ProjectError as e:
                    messages.error(request, e)
                else:
                    email = escape(m.person.email)
                    msg = action.get('msg') % email
                    messages.success(request, msg)

    return redirect_back(request, 'project_list')

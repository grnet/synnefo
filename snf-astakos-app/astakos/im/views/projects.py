# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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
import inflect

engine = inflect.engine()

from django_tables2 import RequestConfig

from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list, object_detail
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.db import transaction

import astakos.im.messages as astakos_messages

from astakos.im import tables
from astakos.im.models import ProjectApplication, ProjectMembership, Project
from astakos.im.util import get_context, restrict_next
from astakos.im.forms import ProjectApplicationForm, AddProjectMembersForm, \
    ProjectSearchForm
from astakos.im.functions import check_pending_app_quota, accept_membership, \
    reject_membership, remove_membership, cancel_membership, leave_project, \
    join_project, enroll_member, can_join_request, can_leave_request, \
    get_related_project_id, approve_application, \
    deny_application, cancel_application, dismiss_application, ProjectError
from astakos.im import settings
from astakos.im.util import redirect_back
from astakos.im.views.util import render_response, _create_object, \
    _update_object, _resources_catalog, ExceptionHandler
from astakos.im.views.decorators import cookie_fix, signed_terms_required,\
    valid_astakos_user_required, login_required

logger = logging.getLogger(__name__)


@cookie_fix
def how_it_works(request):
    return render_response(
        'im/how_it_works.html',
        context_instance=get_context(request))


@require_http_methods(["GET", "POST"])
@cookie_fix
@valid_astakos_user_required
def project_add(request):
    user = request.user
    if not user.is_project_admin():
        ok, limit = check_pending_app_quota(user)
        if not ok:
            m = _(astakos_messages.PENDING_APPLICATION_LIMIT_ADD) % limit
            messages.error(request, m)
            next = reverse('astakos.im.views.project_list')
            next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
            return redirect(next)

    details_fields = ["name", "homepage", "description", "start_date",
                      "end_date", "comments"]
    membership_fields = ["member_join_policy", "member_leave_policy",
                         "limit_on_members_number"]
    resource_catalog, resource_groups = _resources_catalog(for_project=True)
    if resource_catalog is False:
        # on fail resource_groups contains the result object
        result = resource_groups
        messages.error(request, 'Unable to retrieve system resources: %s' %
                       result.reason)
    extra_context = {
        'resource_catalog': resource_catalog,
        'resource_groups': resource_groups,
        'show_form': True,
        'details_fields': details_fields,
        'membership_fields': membership_fields}

    response = None
    with ExceptionHandler(request):
        response = create_app_object(request, extra_context=extra_context)

    if response is not None:
        return response

    next = reverse('astakos.im.views.project_list')
    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


@transaction.commit_on_success
def create_app_object(request, extra_context=None):
    try:
        summary = 'im/projects/projectapplication_form_summary.html'
        return _create_object(
            request,
            template_name='im/projects/projectapplication_form.html',
            summary_template_name=summary,
            extra_context=extra_context,
            post_save_redirect=reverse('project_list'),
            form_class=ProjectApplicationForm,
            msg=_("The %(verbose_name)s has been received and "
                  "is under consideration."))
    except ProjectError as e:
        messages.error(request, e)


def get_user_projects_table(projects, user, prefix):
    apps = ProjectApplication.objects.pending_per_project(projects)
    memberships = user.projectmembership_set.one_per_project()
    objs = ProjectMembership.objects
    accepted_ms = objs.any_accepted_per_project(projects)
    requested_ms = objs.requested_per_project(projects)
    return tables.UserProjectsTable(projects, user=user,
                                    prefix=prefix,
                                    pending_apps=apps,
                                    memberships=memberships,
                                    accepted=accepted_ms,
                                    requested=requested_ms)


@require_http_methods(["GET"])
@cookie_fix
@valid_astakos_user_required
def project_list(request):
    projects = Project.objects.user_accessible_projects(request.user)
    table = get_user_projects_table(projects, user=request.user,
                                    prefix="my_projects_")
    return object_list(
        request,
        projects,
        template_name='im/projects/project_list.html',
        extra_context={
            'is_search': False,
            'table': table,
        })


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_app_cancel(request, application_id):
    next = request.GET.get('next')
    chain_id = None

    with ExceptionHandler(request):
        chain_id = _project_app_cancel(request, application_id)

    if not next:
        if chain_id:
            next = reverse('astakos.im.views.project_detail', args=(chain_id,))
        else:
            next = reverse('astakos.im.views.project_list')

    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


@transaction.commit_on_success
def _project_app_cancel(request, application_id):
    chain_id = None
    try:
        application_id = int(application_id)
        chain_id = get_related_project_id(application_id)
        cancel_application(application_id, request.user)
    except ProjectError as e:
        messages.error(request, e)

    else:
        msg = _(astakos_messages.APPLICATION_CANCELLED)
        messages.success(request, msg)
        return chain_id


@require_http_methods(["GET", "POST"])
@cookie_fix
@valid_astakos_user_required
def project_modify(request, application_id):

    try:
        app = ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    user = request.user
    if not (user.owns_application(app) or user.is_project_admin(app.id)):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    if not user.is_project_admin():
        owner = app.owner
        ok, limit = check_pending_app_quota(owner, project=app.chain)
        if not ok:
            m = _(astakos_messages.PENDING_APPLICATION_LIMIT_MODIFY) % limit
            messages.error(request, m)
            next = reverse('astakos.im.views.project_list')
            next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
            return redirect(next)

    details_fields = ["name", "homepage", "description", "start_date",
                      "end_date", "comments"]
    membership_fields = ["member_join_policy", "member_leave_policy",
                         "limit_on_members_number"]
    resource_catalog, resource_groups = _resources_catalog(for_project=True)
    if resource_catalog is False:
        # on fail resource_groups contains the result object
        result = resource_groups
        messages.error(request, 'Unable to retrieve system resources: %s' %
                       result.reason)
    extra_context = {
        'resource_catalog': resource_catalog,
        'resource_groups': resource_groups,
        'show_form': True,
        'details_fields': details_fields,
        'update_form': True,
        'membership_fields': membership_fields
    }

    response = None
    with ExceptionHandler(request):
        response = update_app_object(request, application_id,
                                     extra_context=extra_context)

    if response is not None:
        return response

    next = reverse('astakos.im.views.project_list')
    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


@transaction.commit_on_success
def update_app_object(request, object_id, extra_context=None):
    try:
        summary = 'im/projects/projectapplication_form_summary.html'
        return _update_object(
            request,
            object_id=object_id,
            template_name='im/projects/projectapplication_form.html',
            summary_template_name=summary,
            extra_context=extra_context,
            post_save_redirect=reverse('project_list'),
            form_class=ProjectApplicationForm,
            msg=_("The %(verbose_name)s has been received and is under "
                  "consideration."))
    except ProjectError as e:
        messages.error(request, e)


@require_http_methods(["GET", "POST"])
@cookie_fix
@valid_astakos_user_required
def project_app(request, application_id):
    return common_detail(request, application_id, project_view=False)


@require_http_methods(["GET", "POST"])
@cookie_fix
@valid_astakos_user_required
def project_detail(request, chain_id):
    return common_detail(request, chain_id)


@transaction.commit_on_success
def addmembers(request, chain_id, addmembers_form):
    if addmembers_form.is_valid():
        try:
            chain_id = int(chain_id)
            map(lambda u: enroll_member(chain_id,
                                        u,
                                        request_user=request.user),
                addmembers_form.valid_users)
        except ProjectError as e:
            messages.error(request, e)


MEMBERSHIP_STATUS_FILTER = {
    0: lambda x: x.requested(),
    1: lambda x: x.any_accepted(),
}


def common_detail(request, chain_or_app_id, project_view=True,
                  template_name='im/projects/project_detail.html',
                  members_status_filter=None):
    project = None
    approved_members_count = 0
    pending_members_count = 0
    remaining_memberships_count = None
    if project_view:
        chain_id = chain_or_app_id
        if request.method == 'POST':
            addmembers_form = AddProjectMembersForm(
                request.POST,
                chain_id=int(chain_id),
                request_user=request.user)
            with ExceptionHandler(request):
                addmembers(request, chain_id, addmembers_form)

            if addmembers_form.is_valid():
                addmembers_form = AddProjectMembersForm()  # clear form data
        else:
            addmembers_form = AddProjectMembersForm()  # initialize form

        project = get_object_or_404(Project, pk=chain_id)
        application = project.application
        if project:
            members = project.projectmembership_set
            approved_members_count = project.members_count()
            pending_members_count = project.count_pending_memberships()
            _limit = application.limit_on_members_number
            if _limit is not None:
                remaining_memberships_count = \
                    max(0, _limit - approved_members_count)
            flt = MEMBERSHIP_STATUS_FILTER.get(members_status_filter)
            if flt is not None:
                members = flt(members)
            else:
                members = members.associated()
            members = members.select_related()
            members_table = tables.ProjectMembersTable(project,
                                                       members,
                                                       user=request.user,
                                                       prefix="members_")
            RequestConfig(request, paginate={"per_page": settings.PAGINATE_BY}
                          ).configure(members_table)

        else:
            members_table = None

    else:
        # is application
        application_id = chain_or_app_id
        application = get_object_or_404(ProjectApplication, pk=application_id)
        members_table = None
        addmembers_form = None

    user = request.user
    is_project_admin = user.is_project_admin(application_id=application.id)
    is_owner = user.owns_application(application)
    if not (is_owner or is_project_admin) and not project_view:
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    if (
        not (is_owner or is_project_admin) and project_view and
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
        queryset=ProjectApplication.objects.select_related(),
        object_id=application.id,
        template_name=template_name,
        extra_context={
            'project_view': project_view,
            'chain_id': chain_or_app_id,
            'application': application,
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
            'remaining_memberships_count': remaining_memberships_count,
        })


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
        accepted = request.user.projectmembership_set.filter(
            state__in=ProjectMembership.ACCEPTED_STATES).values_list(
                'project', flat=True)

        projects = Project.objects.search_by_name(q)
        projects = projects.filter(Project.o_state_q(Project.O_ACTIVE))
        projects = projects.exclude(id__in=accepted).select_related(
            'application', 'application__owner', 'application__applicant')

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


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_join(request, chain_id):
    next = request.GET.get('next')
    if not next:
        next = reverse('astakos.im.views.project_detail',
                       args=(chain_id,))

    with ExceptionHandler(request):
        _project_join(request, chain_id)

    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


@transaction.commit_on_success
def _project_join(request, chain_id):
    try:
        chain_id = int(chain_id)
        membership = join_project(chain_id, request.user)
        if membership.state != membership.REQUESTED:
            m = _(astakos_messages.USER_JOINED_PROJECT)
        else:
            m = _(astakos_messages.USER_JOIN_REQUEST_SUBMITTED)
        messages.success(request, m)
    except ProjectError as e:
        messages.error(request, e)


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_leave(request, memb_id):
    next = request.GET.get('next')
    if not next:
        next = reverse('astakos.im.views.project_list')

    with ExceptionHandler(request):
        _project_leave(request, memb_id)

    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


@transaction.commit_on_success
def _project_leave(request, memb_id):
    try:
        memb_id = int(memb_id)
        auto_accepted = leave_project(memb_id, request.user)
        if auto_accepted:
            m = _(astakos_messages.USER_LEFT_PROJECT)
        else:
            m = _(astakos_messages.USER_LEAVE_REQUEST_SUBMITTED)
        messages.success(request, m)
    except ProjectError as e:
        messages.error(request, e)


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_cancel_member(request, memb_id):
    next = request.GET.get('next')
    if not next:
        next = reverse('astakos.im.views.project_list')

    with ExceptionHandler(request):
        _project_cancel_member(request, memb_id)

    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


@transaction.commit_on_success
def _project_cancel_member(request, memb_id):
    try:
        cancel_membership(memb_id, request.user)
        m = _(astakos_messages.USER_REQUEST_CANCELLED)
        messages.success(request, m)
    except ProjectError as e:
        messages.error(request, e)


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_accept_member(request, memb_id):

    with ExceptionHandler(request):
        _project_accept_member(request, memb_id)

    return redirect_back(request, 'project_list')


@transaction.commit_on_success
def _project_accept_member(request, memb_id):
    try:
        memb_id = int(memb_id)
        m = accept_membership(memb_id, request.user)
    except ProjectError as e:
        messages.error(request, e)

    else:
        email = escape(m.person.email)
        msg = _(astakos_messages.USER_MEMBERSHIP_ACCEPTED) % email
        messages.success(request, msg)


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_remove_member(request, memb_id):

    with ExceptionHandler(request):
        _project_remove_member(request, memb_id)

    return redirect_back(request, 'project_list')


@transaction.commit_on_success
def _project_remove_member(request, memb_id):
    try:
        memb_id = int(memb_id)
        m = remove_membership(memb_id, request.user)
    except ProjectError as e:
        messages.error(request, e)
    else:
        email = escape(m.person.email)
        msg = _(astakos_messages.USER_MEMBERSHIP_REMOVED) % email
        messages.success(request, msg)


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def project_reject_member(request, memb_id):

    with ExceptionHandler(request):
        _project_reject_member(request, memb_id)

    return redirect_back(request, 'project_list')


@transaction.commit_on_success
def _project_reject_member(request, memb_id):
    try:
        memb_id = int(memb_id)
        m = reject_membership(memb_id, request.user)
    except ProjectError as e:
        messages.error(request, e)
    else:
        email = escape(m.person.email)
        msg = _(astakos_messages.USER_MEMBERSHIP_REJECTED) % email
        messages.success(request, msg)


@require_http_methods(["POST"])
@signed_terms_required
@login_required
@cookie_fix
def project_app_approve(request, application_id):

    if not request.user.is_project_admin():
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    try:
        ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    with ExceptionHandler(request):
        _project_app_approve(request, application_id)

    chain_id = get_related_project_id(application_id)
    if not chain_id:
        return redirect_back(request, 'project_list')
    return redirect(reverse('project_detail', args=(chain_id,)))


@transaction.commit_on_success
def _project_app_approve(request, application_id):
    approve_application(application_id)


@require_http_methods(["POST"])
@signed_terms_required
@login_required
@cookie_fix
def project_app_deny(request, application_id):

    reason = request.POST.get('reason', None)
    if not reason:
        reason = None

    if not request.user.is_project_admin():
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    try:
        ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    with ExceptionHandler(request):
        _project_app_deny(request, application_id, reason)

    return redirect(reverse('project_list'))


@transaction.commit_on_success
def _project_app_deny(request, application_id, reason):
    deny_application(application_id, reason=reason)


@require_http_methods(["POST"])
@signed_terms_required
@login_required
@cookie_fix
def project_app_dismiss(request, application_id):
    try:
        app = ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    if not request.user.owns_application(app):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    with ExceptionHandler(request):
        _project_app_dismiss(request, application_id)

    chain_id = None
    chain_id = get_related_project_id(application_id)
    if chain_id:
        next = reverse('project_detail', args=(chain_id,))
    else:
        next = reverse('project_list')
    return redirect(next)


def _project_app_dismiss(request, application_id):
    # XXX: dismiss application also does authorization
    dismiss_application(application_id, request_user=request.user)


@require_http_methods(["GET", "POST"])
@valid_astakos_user_required
def project_members(request, chain_id, members_status_filter=None,
                    template_name='im/projects/project_members.html'):
    project = get_object_or_404(Project, pk=chain_id)

    user = request.user
    if not user.owns_project(project) and not user.is_project_admin():
        return redirect(reverse('index'))

    return common_detail(request, chain_id,
                         members_status_filter=members_status_filter,
                         template_name=template_name)


@require_http_methods(["POST"])
@valid_astakos_user_required
def project_members_action(request, chain_id, action=None, redirect_to=''):

    actions_map = {
        'remove': _project_remove_member,
        'accept': _project_accept_member,
        'reject': _project_reject_member
    }

    if not action in actions_map.keys():
        raise PermissionDenied

    member_ids = request.POST.getlist('members')
    project = get_object_or_404(Project, pk=chain_id)

    user = request.user
    if not user.owns_project(project) and not user.is_project_admin():
        return redirect(reverse('index'))

    logger.info("Batch members action from %s (chain: %r, action: %s, "
                "members: %r)", user.log_display, chain_id, action, member_ids)

    action_func = actions_map.get(action)
    for member_id in member_ids:
        member_id = int(member_id)
        with ExceptionHandler(request):
            action_func(request, member_id)

    return redirect_back(request, 'project_list')

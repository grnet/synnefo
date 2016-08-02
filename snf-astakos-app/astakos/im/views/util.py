# Copyright (C) 2010-2016 GRNET S.A.
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
import astakos.im.messages as astakos_messages

from astakos.im import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import RequestContext, loader as template_loader
from django.utils.translation import ugettext as _
from astakos.im import transaction

from synnefo.lib.ordereddict import OrderedDict

from astakos.im import presentation
from astakos.im.util import model_to_dict
from astakos.im import tables
from astakos.im.models import Resource, ProjectApplication, ProjectMembership
from astakos.im import functions
from astakos.im.util import get_context, restrict_next, restrict_reverse

logger = logging.getLogger(__name__)


class ExceptionHandler(object):
    def __init__(self, request):
        self.request = request

    def __enter__(self):
        pass

    def __exit__(self, exc_type, value, traceback):
        if value is not None:  # exception
            logger.exception(value)
            m = _(astakos_messages.GENERIC_ERROR)
            messages.error(self.request, m)
            return True  # suppress exception


def render_response(template, tab=None, status=200, context_instance=None,
                    **kwargs):
    """
    Calls ``django.template.loader.render_to_string`` with an additional
    ``tab`` keyword argument and returns an ``django.http.HttpResponse``
    with the specified ``status``.
    """
    if tab is None:
        tab = template.partition('_')[0].partition('.html')[0]
    kwargs.setdefault('tab', tab)
    html = template_loader.render_to_string(
        template, kwargs, context_instance=context_instance)
    response = HttpResponse(html, status=status)
    return response


def sorted_resources(resource_grant_or_quota_set):
    meta = presentation.RESOURCES
    order = meta.get('resources_order', [])
    resources = list(resource_grant_or_quota_set)

    def order_key(item):
        name = item.resource.name
        if name in order:
            return order.index(name)
        return -1
    return sorted(resources, key=order_key)


def _resources_catalog(as_dict=False):
    """
    `resource_catalog` contains a list of tuples. Each tuple contains the group
    key the resource is assigned to and resources list of dicts that contain
    resource information.
    `resource_groups` contains information about the groups
    """
    # presentation data
    resources_meta = presentation.RESOURCES
    resource_groups = resources_meta.get('groups', {})
    resource_catalog = ()
    resource_keys = []

    # resources in database
    resource_details = map(lambda obj: model_to_dict(obj, exclude=[]),
                           Resource.objects.all())
    # initialize resource_catalog to contain all group/resource information
    for r in resource_details:
        if not r.get('group') in resource_groups:
            resource_groups[r.get('group')] = {'icon': 'unknown'}

    resource_keys = [r.get('str_repr') for r in resource_details]
    resource_catalog = [[g, filter(lambda r: r.get('group', '') == g,
                                   resource_details)] for g in resource_groups]

    # order groups, also include unknown groups
    groups_order = resources_meta.get('groups_order')
    for g in resource_groups.keys():
        if not g in groups_order:
            groups_order.append(g)

    # order resources, also include unknown resources
    resources_order = resources_meta.get('resources_order')
    for r in resource_keys:
        if not r in resources_order:
            resources_order.append(r)

    # sort catalog groups
    resource_catalog = sorted(resource_catalog,
                              key=lambda g: groups_order.index(g[0]))

    # sort groups
    def groupindex(g):
        return groups_order.index(g[0])
    resource_groups_list = sorted([(k, v) for k, v in resource_groups.items()],
                                  key=groupindex)
    resource_groups = OrderedDict(resource_groups_list)

    # sort resources
    def resourceindex(r):
        return resources_order.index(r['str_repr'])

    for index, group in enumerate(resource_catalog):
        resource_catalog[index][1] = sorted(resource_catalog[index][1],
                                            key=resourceindex)
        if len(resource_catalog[index][1]) == 0:
            resource_catalog.pop(index)
            for gindex, g in enumerate(resource_groups):
                if g[0] == group[0]:
                    resource_groups.pop(gindex)

    # filter out resources which user cannot request in a project application
    for group, resources in list(resource_catalog):
        for resource in resources:
            if not resource.get('ui_visible'):
                resources.remove(resource)

    # cleanup empty groups
    resource_catalog_new = []
    for group, resources in list(resource_catalog):
        if len(resources) == 0:
            resource_groups.pop(group)
        else:
            resource_catalog_new.append((group, resources))

    if as_dict:
        resource_catalog_new = OrderedDict(resource_catalog_new)
        for name, resources in resource_catalog_new.iteritems():
            _rs = OrderedDict()
            for resource in resources:
                _rs[resource.get('name')] = resource
            resource_catalog_new[name] = _rs
        resource_groups = OrderedDict(resource_groups)

    return resource_catalog_new, resource_groups


def get_user_projects_table(projects, user, prefix, request=None):
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
                                    requested=requested_ms,
                                    request=request)


@transaction.commit_on_success
def handle_valid_members_form(request, project_id, addmembers_form):
    if addmembers_form.is_valid():
        try:
            users = addmembers_form.valid_users
            for user in users:
                functions.enroll_member_by_email(project_id, user.email,
                                                 request_user=request.user)
        except functions.ProjectError as e:
            messages.error(request, e)


def redirect_to_next(request, default_resolve, *args, **kwargs):
    next = kwargs.pop('next', None)
    if not next:
        default = restrict_reverse(default_resolve, *args,
                                   restrict_domain=settings.COOKIE_DOMAIN,
                                   **kwargs)
        next = request.GET.get('next', default)

    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)
    return redirect(next)


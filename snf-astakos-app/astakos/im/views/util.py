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

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.xheaders import populate_xheaders
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import RequestContext, loader as template_loader
from django.utils.translation import ugettext as _
from django.views.generic.create_update import apply_extra_context, \
    get_model_and_form_class, lookup_object

from synnefo.lib.ordereddict import OrderedDict

from astakos.im import presentation
from astakos.im.util import model_to_dict
from astakos.im.models import Resource
import astakos.im.messages as astakos_messages
import logging

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


def _create_object(request, model=None, template_name=None,
                   template_loader=template_loader, extra_context=None,
                   post_save_redirect=None, login_required=False,
                   context_processors=None, form_class=None, msg=None,
                   summary_template_name=None):
    """
    Based of django.views.generic.create_update.create_object which displays a
    summary page before creating the object.
    """

    if extra_context is None:
        extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    model, form_class = get_model_and_form_class(model, form_class)
    extra_context['edit'] = 0
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
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
                if not msg:
                    msg = _(
                        "The %(verbose_name)s was created successfully.")
                msg = msg % model._meta.__dict__
                messages.success(request, msg, fail_silently=True)
                return redirect(post_save_redirect, new_object)
    else:
        form = form_class()

    # Create the template, context, response
    if not template_name:
        template_name = "%s/%s_form.html" % \
            (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form
    }, context_processors)
    apply_extra_context(extra_context, c)
    return HttpResponse(t.render(c))


def _update_object(request, model=None, object_id=None, slug=None,
                   slug_field='slug', template_name=None,
                   template_loader=template_loader, extra_context=None,
                   post_save_redirect=None, login_required=False,
                   context_processors=None, template_object_name='object',
                   form_class=None, msg=None, summary_template_name=None):
    """
    Based of django.views.generic.create_update.update_object which displays a
    summary page before updating the object.
    """

    if extra_context is None:
        extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    model, form_class = get_model_and_form_class(model, form_class)
    obj = lookup_object(model, object_id, slug, slug_field)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=obj)
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
                obj = form.save()
                if not msg:
                    msg = _(
                        "The %(verbose_name)s was created successfully.")
                msg = msg % model._meta.__dict__
                messages.success(request, msg, fail_silently=True)
                return redirect(post_save_redirect, obj)
    else:
        form = form_class(instance=obj)

    if not template_name:
        template_name = "%s/%s_form.html" % \
            (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form,
        template_object_name: obj,
    }, context_processors)
    apply_extra_context(extra_context, c)
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, model,
                      getattr(obj, obj._meta.pk.attname))
    return response


def _resources_catalog(for_project=False, for_usage=False):
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
    exclude = resources_meta.get('exclude_from_usage', [])
    for group_index, group_resources in enumerate(list(resource_catalog)):
        group, resources = group_resources
        for index, resource in list(enumerate(resources)):
            if for_project and not resource.get('allow_in_projects'):
                resources.remove(resource)
            if resource.get('str_repr') in exclude and for_usage:
                resources.remove(resource)

    # cleanup empty groups
    for group_index, group_resources in enumerate(list(resource_catalog)):
        group, resources = group_resources
        if len(resources) == 0:
            resource_catalog.pop(group_index)
            resource_groups.pop(group)

    return resource_catalog, resource_groups

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
import json
from importlib import import_module

from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from urllib import unquote

import astakosclient
from snf_django.lib import astakos
from synnefo_branding.utils import render_to_string
from snf_django.lib.api import faults


from astakos.im.messages import PLAIN_EMAIL_SUBJECT as sample_subject
from astakos.im import settings as astakos_settings
from astakos.admin import stats as astakos_stats
from synnefo.admin import stats as cyclades_stats

from synnefo_admin.admin.exceptions import AdminHttp404, AdminHttp405
from synnefo_admin import admin_settings

from synnefo_admin.admin import exceptions
from synnefo_admin.admin.utils import (conditionally_gzip_page,
                                       customize_details_context, admin_log,
                                       default_view)

from synnefo.ui.views import UI_MEDIA_URL

JSON_MIMETYPE = "application/json"

logger = logging.getLogger(__name__)


# Helper functions ###


def get_view_module(view_type):
    """Import module for model view.

    We will import only modules for views that are specified in the ADMIN_VIEWS
    setting.
    """
    if view_type in admin_settings.ADMIN_VIEWS:
        # The modules will not be loaded per-call but only once.
        return import_module('synnefo_admin.admin.resources.%ss.views' % view_type)
    return None


def get_view_module_or_404(view_type):
    """Try to import a view module or raise 404."""
    if not view_type:
        raise AdminHttp404("No category provided.")

    mod = get_view_module(view_type)
    if not mod:
        raise AdminHttp404("No category found with this name: %s" % view_type)
    return mod


def get_json_view_or_404(view_type):
    """Try to import a json view or raise 404."""
    mod = get_view_module_or_404(view_type)
    # We expect that the module has a JSON_CLASS attribute with the appropriate
    # subclass of django-eztable's DatatablesView.
    return mod.JSON_CLASS.as_view()


def get_token_from_cookie(request, cookiename):
    """Extract token from provided cookie.

    Extract token from the cookie name provided. Cookie should be in the same
    form as astakos service sets its cookie contents::

        <user_uniq>|<user_token>
    """
    try:
        cookie_content = unquote(request.COOKIES.get(cookiename, None))
        return cookie_content.split("|")[1]
    except AttributeError:
        pass

    return None


# Security functions ###


def admin_user_required(func, permitted_groups=admin_settings.\
                        ADMIN_PERMITTED_GROUPS):
    """
    Django view wrapper that checks if identified request user has admin
    permissions (exists in admin group)
    """
    def wrapper(request, *args, **kwargs):
        if not admin_settings.ADMIN_ENABLED:
            # we must never raise an AdminHttp404 exception here.
            raise Http404

        token = get_token_from_cookie(request, admin_settings.AUTH_COOKIE_NAME)
        astakos.get_user(request, settings.ASTAKOS_AUTH_URL,
                         fallback_token=token, logger=logger)
        if hasattr(request, 'user') and request.user:
            groups = request.user['access']['user']['roles']
            groups = [g["name"] for g in groups]

            if not set(groups) & set(permitted_groups):
                logger.debug("Failed to access admin view %r. No valid admin "
                             "group (%r) matches user groups (%r)",
                             request.user_uniq, permitted_groups, groups)
                raise PermissionDenied
        else:
            logger.debug("Failed to access admin view %r. No authenticated "
                         "user found.", request.user_uniq)
            logger.debug("auth_url (%s)", settings.ASTAKOS_AUTH_URL)
            raise PermissionDenied

        logging.debug("User %s accessed admininterface view (%s)",
                      request.user_uniq, request.path)
        return func(request, *args, **kwargs)

    return wrapper


# View functions ###

default_dict = {
    'ADMIN_MEDIA_URL': admin_settings.ADMIN_MEDIA_URL,
    'UI_MEDIA_URL': UI_MEDIA_URL,
    'mail': {
        'sender': astakos_settings.SERVER_EMAIL,
        'subject': sample_subject,
        'body': render_to_string('im/plain_email.txt', {
            'baseurl': astakos_settings.BASE_URL,
            'support': astakos_settings.CONTACT_EMAIL}).replace('\n\n\n', '\n'),
        'legend': {
            'Full name': "{{ full_name }}",
            'First name': "{{ first_name }}",
            'Last name': "{{ last_name }}",
            'Email': "{{ email }}",
        }
    },
    'views': admin_settings.ADMIN_VIEWS,
}


@admin_user_required
def logout(request):
    """Logout view."""
    admin_log(request)
    auth_token = request.user['access']['token']['id']
    ac = astakosclient.AstakosClient(auth_token, settings.ASTAKOS_AUTH_URL,
                                     retry=2, use_pool=True, logger=logger)
    logout_url = ac.ui_url + '/logout'

    return HttpResponseRedirect(logout_url)


@admin_user_required
def home(request):
    """Home view."""
    admin_log(request)
    return direct_to_template(request, "admin/home.html",
                              extra_context=default_dict)


@admin_user_required
def stats(request):
    """Stats view."""
    admin_log(request)
    return direct_to_template(request, "admin/stats.html",
                              extra_context=default_dict)


@admin_user_required
def charts(request):
    """Charts view."""
    admin_log(request)
    return direct_to_template(request, "admin/charts.html",
                              extra_context=default_dict)


@admin_user_required
def stats_component(request, component):
    """Mirror public stats view for cyclades/astakos.

    This stats view will import the get_public_stats function of
    cyclades/astakos and return its results to the caller.
    """
    admin_log(request, component=component)
    data = {}
    status = 200
    if component == 'astakos':
        data = astakos_stats.get_public_stats()
    elif component == 'cyclades':
        data = cyclades_stats.get_public_stats()
    else:
        status = 404
    return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder),
                        mimetype=JSON_MIMETYPE, status=status)


@admin_user_required
def stats_component_details(request, component):
    """Mirror detailed stats view for cyclades/astakos.

    This stats view will import the get_astakos/cyclades_stats function and
    return its results to the caller.
    """
    admin_log(request, component=component)
    data = {}
    status = 200
    if component == 'astakos':
        data = astakos_stats.get_astakos_stats()
    elif component == 'cyclades':
        data = cyclades_stats.get_cyclades_stats()
    else:
        status = 404
    return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder),
                        mimetype=JSON_MIMETYPE, status=status)


@admin_user_required
@conditionally_gzip_page
def json_list(request, type):
    """Return a class-based view based on the given type."""
    admin_log(request, type=type)

    content_types = request.META.get("HTTP_ACCEPT", "")
    if "application/json" not in content_types:
        raise AdminHttp405("""\
The JSON content of this page is for internal use.
You cannot view it on your browser.""")
    view = get_json_view_or_404(type)
    return view(request)


@admin_user_required
def details(request, type, id):
    """Admin-Interface generic details view."""
    admin_log(request, type=type, id=id)

    mod = get_view_module_or_404(type)
    context = mod.details(request, id)
    customize_details_context(context)
    context.update(default_dict)
    context.update({'view_type': 'details'})

    template = mod.templates['details']
    return direct_to_template(request, template, extra_context=context)


@admin_user_required
def catalog(request, type=default_view()):
    """Admin-Interface generic list view."""
    admin_log(request, type=type)

    mod = get_view_module_or_404(type)
    context = mod.catalog(request)
    context.update(default_dict)
    context.update({'view_type': 'list'})

    template = mod.templates['list']
    return direct_to_template(request, template, extra_context=context)


@csrf_exempt
@admin_user_required
def admin_actions(request):
    """Entry-point for all admin actions.

    Expects a JSON with the following fields: <TODO>
    """
    admin_log(request, json=request.REQUEST)
    status = 200
    response = {
        'result': "All actions finished successfully.",
        'error_ids': [],
    }

    if request.method != "POST":
        status = 405
        response['result'] = "Only POST is allowed."

    objs = json.loads(request.body)
    request.POST = objs

    target = objs['target']
    op = objs['op']
    ids = objs['ids']
    if type(ids) is not list:
        ids = ids.replace('[', '').replace(']', '').replace(' ', '').split(',')

    try:
        mod = get_view_module_or_404(target)
    except Http404:
        status = 404
        response['result'] = "You have requested an unknown operation."

    for id in ids:
        try:
            mod.do_action(request, op, id)
        except faults.BadRequest as e:
            status = 400
            response['result'] = e.message
            response['error_ids'].append(id)
        except exceptions.AdminActionNotPermitted:
            status = 403
            response['result'] = "You are not allowed to do this operation."
            response['error_ids'].append(id)
        except faults.NotAllowed:
            status = 403
            response['result'] = "You are not allowed to do this operation."
            response['error_ids'].append(id)
        except exceptions.AdminActionUnknown:
            status = 404
            response['result'] = "You have requested an unknown operation."
            break
        except exceptions.AdminActionNotImplemented:
            status = 501
            response['result'] = "You have requested an unimplemented action."
            break
        except exceptions.AdminActionCannotApply:
            status = 400
            response['result'] = """
                You have requested an action that cannot apply to a target.
                """
            response['error_ids'].append(id)
        except Exception as e:
            logging.exception("Uncaught exception")
            status = 500
            response['result'] = e.message
            response['error_ids'].append(id)

    if hasattr(mod, 'wait_action'):
        wait_ids = set(ids) - set(response['error_ids'])
        for id in wait_ids:
            mod.wait_action(request, op, id)

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder),
                        mimetype=JSON_MIMETYPE, status=status)

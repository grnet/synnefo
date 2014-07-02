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

import sys
import re
import logging
import json
from importlib import import_module

from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from urllib import unquote

import astakosclient
from snf_django.lib import astakos
from synnefo_branding.utils import render_to_string
from snf_django.lib.api import faults

from astakos.im.messages import PLAIN_EMAIL_SUBJECT as sample_subject
from astakos.im import settings as astakos_settings

# Import model-specific views
import synnefo_admin.admin.users.views as user_views
import synnefo_admin.admin.vms.views as vm_views
import synnefo_admin.admin.volumes.views as volume_views
import synnefo_admin.admin.networks.views as network_views
import synnefo_admin.admin.ips.views as ip_views
import synnefo_admin.admin.projects.views as project_views
from synnefo_admin.admin import groups as group_views
from synnefo_admin.admin import auth_providers as auth_provider_views
from synnefo_admin.admin import actions
from synnefo_admin.admin.utils import conditionally_gzip_page

from synnefo.ui.views import UI_MEDIA_URL

JSON_MIMETYPE = "application/json"

logger = logging.getLogger(__name__)

ADMIN_MEDIA_URL = getattr(settings, 'ADMIN_MEDIA_URL',
                          settings.MEDIA_URL + 'admin/')

IP_SEARCH_REGEX = re.compile('([0-9]+)(?:\.[0-9]+){3}')
VM_SEARCH_REGEX = re.compile('vm(-){0,}(?P<vmid>[0-9]+)')

AUTH_COOKIE_NAME = getattr(settings, 'ADMIN_AUTH_COOKIE_NAME',
                           getattr(settings, 'UI_AUTH_COOKIE_NAME',
                                   '_pithos2_a'))
PERMITTED_GROUPS = getattr(settings, 'ADMIN_PERMITTED_GROUPS',
                           ['admin-readonly', 'admin', 'superadmin'])
SHOW_DELETED_VMS = getattr(settings, 'ADMIN_SHOW_DELETED_VMS', False)


### Helper functions

def get_view_module(view_type):
    try:
        # This module will not be reloaded again as it's probably cached.
        return import_module('synnefo_admin.admin.%ss.views' % view_type)
    except ImportError:
        return import_module('synnefo_admin.admin.%ss' % view_type)
    except ImportError:
        logging.error("Cannot get view for type: %s", view_type)
        raise Http404


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


### Security functions

def token_check(func):
    """
    Mimic csrf security check using user auth token.
    """
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user'):
            raise PermissionDenied

        token = request.POST.get('token', None)
        if token:
            try:
                req_token = request.user["access"]["token"]["id"]
                if token == req_token:
                    return func(request, *args, **kwargs)
            except KeyError:
                pass

        raise PermissionDenied

    return wrapper


def admin_user_required(func, permitted_groups=PERMITTED_GROUPS):
    """
    Django view wrapper that checks if identified request user has admin
    permissions (exists in admin group)
    """
    def wrapper(request, *args, **kwargs):
        ADMIN_ENABLED = getattr(settings, 'ADMIN_ENABLED', True)
        if not ADMIN_ENABLED:
            raise Http404

        token = get_token_from_cookie(request, AUTH_COOKIE_NAME)
        logging.info("My token: %s", token)
        astakos.get_user(request, settings.ASTAKOS_AUTH_URL,
                         fallback_token=token, logger=logger)
        if hasattr(request, 'user') and request.user:
            groups = request.user['access']['user']['roles']
            groups = [g["name"] for g in groups]

            if not groups:
                logger.info("Failed to access admin view. User: %r",
                            request.user_uniq)
                raise PermissionDenied

            has_perm = False
            for g in groups:
                if g in permitted_groups:
                    has_perm = True

            if not has_perm:
                logger.info("Failed to access admin view %r. No valid "
                            "admin group (%r) matches user groups (%r)",
                            request.user_uniq, permitted_groups, groups)
                raise PermissionDenied
        else:
            logger.info("Failed to access admin view %r. No authenticated "
                        "user found.", request.user_uniq)
            logger.info("auth_url (%s)", settings.ASTAKOS_AUTH_URL)
            raise PermissionDenied

        logging.info("User %s accessed admininterface view (%s)",
                     request.user_uniq, request.path)
        return func(request, *args, **kwargs)

    return wrapper


### View functions

default_dict = {
    'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
    'UI_MEDIA_URL': UI_MEDIA_URL,
    'mail': {
        'subject': sample_subject,
        'body': render_to_string('im/plain_email.txt', {
            'baseurl': astakos_settings.BASE_URL,
            'site_name': astakos_settings.SITENAME,
            'support': astakos_settings.CONTACT_EMAIL}).replace('\n\n\n', '\n'),
        'legend': {
            'Full name': "{{ full_name }}",
            'First name': "{{ firstname }}",
            'Last name': "{{ last_name }}",
            'Email': "{{ email }}",
        }
    },
    'item_lists': (('Users', 'user'),
                   ('VMs', 'vm'),
                   ('Volumes', 'volume'),
                   ('Networks', 'network'),
                   ('IPs', 'ip'),
                   ('Projects', 'project'),
                   ('User Groups', 'group'),
                   #('User Auth Providers', 'auth_provider'),
                   )
}


@admin_user_required
def logout(request):
    try:
        auth_token = request.user['access']['token']['id']
        ac = astakosclient.AstakosClient(auth_token, settings.ASTAKOS_AUTH_URL,
                                         retry=2, use_pool=True, logger=logger)
        logout_url = ac.ui_url + '/logout'
    except Exception as e:
        logger.exception("Why?")
        raise e

    return HttpResponseRedirect(logout_url)


@admin_user_required
def home(request):
    """Home view."""
    return direct_to_template(request, "admin/home.html",
                              extra_context=default_dict)


@admin_user_required
def charts(request):
    """Dummy view for charts."""
    return direct_to_template(request, "admin/charts.html",
                              extra_context=default_dict)


@admin_user_required
def stats(request):
    """Dummy view for stats."""
    return direct_to_template(request, "admin/stats.html",
                              extra_context=default_dict)


@admin_user_required
@conditionally_gzip_page
def json_list(request, type):
    """Return a class-based view based on the given type."""
    logging.info("Request for json. Type: %s", type)

    if type == 'user':
        return user_views.UserJSONView.as_view()(request)
    elif type == 'project':
        return project_views.ProjectJSONView.as_view()(request)
    elif type == 'vm':
        return vm_views.VMJSONView.as_view()(request)
    elif type == 'volume':
        return volume_views.VolumeJSONView.as_view()(request)
    elif type == 'network':
        return network_views.NetworkJSONView.as_view()(request)
    elif type == 'ip':
        return ip_views.IPJSONView.as_view()(request)
    elif type == 'group':
        return group_views.GroupJSONView.as_view()(request)
    elif type == 'auth_provider':
        return auth_provider_views.AstakosUserAuthProviderJSONView.as_view()(request)
    else:
        logging.error("JSON view does not exist")
        raise Http404


@csrf_exempt
@admin_user_required
def details(request, type, id):
    """Admin-Interface generic details view."""
    logging.info("Request for details. Type: %s, ID: %s", type, id)

    mod = get_view_module(type)
    context = mod.details(request, id)
    context.update(default_dict)
    context.update({'view_type': 'details'})

    template = mod.templates['details']
    return direct_to_template(request, template, extra_context=context)


@admin_user_required
def catalog(request, type):
    """Admin-Interface generic list view."""
    logging.info("Request for list. Type: %s", type)

    mod = get_view_module(type)
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
    status = 200
    response = {
        'result': "All actions finished successfully",
        'error_ids': [],
    }

    if request.method != "POST":
        status = 405
        response['result'] = "Only POST is allowed"

    logging.info("This is the request %s", request.body)
    objs = json.loads(request.body)
    request.POST = objs
    logging.info("This is the decoded dictionary %s", request.POST)

    target = objs['target']
    op = objs['op']
    ids = objs['ids']
    if type(ids) is not list:
        ids = ids.replace('[', '').replace(']', '').replace(' ', '').split(',')

    try:
        mod = get_view_module(target)
    except Http404:
        status = 404
        response['result'] = "You have requested an unknown operation."

    for id in ids:
        try:
            mod.do_action(request, op, id)
        except faults.BadRequest:
            status = 400
            response['result'] = "Bad request."
            response['error_ids'].append(id)
        except actions.AdminActionNotPermitted:
            status = 403
            response['result'] = "You are not allowed to do this operation."
            response['error_ids'].append(id)
        except faults.NotAllowed:
            status = 403
            response['result'] = "You are not allowed to do this operation."
            response['error_ids'].append(id)
        except actions.AdminActionUnknown:
            status = 404
            response['result'] = "You have requested an unknown operation."
            break
        except actions.AdminActionNotImplemented:
            status = 501
            response['result'] = "You have requested an unimplemented action."
            break

    if hasattr(mod, 'wait_action'):
        wait_ids = set(ids) - set(response['error_ids'])
        for id in wait_ids:
            mod.wait_action(request, op, id)

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder),
                        mimetype=JSON_MIMETYPE, status=status)

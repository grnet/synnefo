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


import re
import logging
import functools

from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt

from urllib import unquote

import astakosclient
from snf_django.lib import astakos
from synnefo_branding.utils import render_to_string

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
import copy

# for django-eztables
from django.template import add_to_builtins
add_to_builtins('eztables.templatetags.eztables')

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


def search_by_ip(request, search_query):
    """Search IP history for all uses of an IP address."""
    auth_token = request.user['access']['token']['id']
    astakos_client = astakosclient.AstakosClient(auth_token,
                                                 settings.ASTAKOS_AUTH_URL,
                                                 retry=2, use_pool=True,
                                                 logger=logger)

    ips = IPAddressLog.objects.filter(address=search_query)\
        .order_by("allocated_at")

    for ip in ips:
        # Annotate IPs with the VM, Network and account attributes
        ip.vm = VirtualMachine.objects.get(id=ip.server_id)
        ip.network = Network.objects.get(id=ip.network_id)
        userid = ip.vm.userid

        try:
            ip.account = astakos_client.get_username(userid)
        except:
            ip.account = userid
            logger.info("Failed to resolve '%s' into account" % userid)

    user_context = {
        'ip_exists': bool(ips),
        'ips': ips,
        'search_query': search_query,
        'token': auth_token,
        'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
        'UI_MEDIA_URL': UI_MEDIA_URL
    }

    return direct_to_template(request, "admin/ip.html",
                              extra_context=user_context)


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
            'support': astakos_settings.CONTACT_EMAIL})
    },
    'item_lists': (('Users', 'user'),
                   ('VMs', 'vm'),
                   ('Volumes', 'volume'),
                   ('Networks', 'network'),
                   ('IPs', 'ip'),
                   ('Projects', 'project'),
                   ('User Groups', 'group'),
                   ('User Auth Providers', 'auth_provider'))
}


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


@csrf_exempt
@admin_user_required
def details(request, type, id):
    """Admin-Interface generic details view."""
    logging.info("Request for details. Type: %s, ID: %s", type, id)

    if type == 'user':
        context = user_views.details(request, id)
        template = user_views.templates['details']
    elif type == 'project':
        context = project_views.details(request, id)
        template = project_views.templates['details']
    elif type == 'vm':
        context = vm_views.details(request, id)
        template = vm_views.templates['details']
    elif type == 'network':
        context = network_views.details(request, id)
        template = network_views.templates['details']
    elif type == 'volume':
        context = volume_views.details(request, id)
        template = volume_views.templates['details']
    elif type == 'ip':
        context = ip_views.details(request, id)
        template = ip_views.templates['details']
    else:
        logging.error("Wrong type: %s", type)
        # TODO: Return an error here
        return

    context.update(default_dict)
    context.update({'view_type': 'details'})
    return direct_to_template(request, template, extra_context=context)


@admin_user_required
def catalog(request, type):
    """Admin-Interface generic list view."""
    logging.info("Request for list. Type: %s", type)

    if type == 'user':
        context = user_views.catalog(request)
        template = user_views.templates['list']
    elif type == 'project':
        context = project_views.catalog(request)
        template = project_views.templates['list']
    elif type == 'vm':
        context = vm_views.catalog(request)
        template = vm_views.templates['list']
    elif type == 'volume':
        context = volume_views.catalog(request)
        template = volume_views.templates['list']
    elif type == 'network':
        context = network_views.catalog(request)
        template = network_views.templates['list']
    elif type == 'ip':
        context = ip_views.catalog(request)
        template = ip_views.templates['list']
    elif type == 'group':
        context = group_views.catalog(request)
        template = group_views.templates['list']
    elif type == 'auth_provider':
        context = auth_provider_views.catalog(request)
        template = auth_provider_views.templates['list']
    else:
        logging.error("Wrong type: %s", type)
        # TODO: Return an error here
        return

    context.update(default_dict)
    context.update({'view_type': 'list'})

    return direct_to_template(request, template, extra_context=context)


def _admin_actions_id(request, target, op, id):
    if target == 'user':
        user_views.do_action(request, op, id)
    elif target == 'vm':
        vm_views.do_action(request, op, id)
    elif target == 'volume':
        volume_views.do_action(request, op, id)
    elif target == 'network':
        network_views.do_action(request, op, id)
    elif target == 'ip':
        ip_views.do_action(request, op, id)
    elif target == 'project':
        project_views.do_action(request, op, id)
    else:
        raise Exception("Wrong target: %s", target)


@csrf_exempt
@admin_user_required
def admin_actions_id(request, target, op, id):
    logging.info("Entered admin actions view for a specific ID")

    if request.method == "POST":
        logging.info("POST body: %s", request.POST)

    _admin_actions_id(request, target, op, id)

    return HttpResponseRedirect(redirect)


@csrf_exempt
@admin_user_required
def admin_actions(request):
    """Entry-point for all admin actions.

    Expects a JSON with the following fields: <TODO>
    """
    logging.info("Entered admin actions view")

    if request.method == "POST":
        logging.info("POST body: %s", request.POST)

    target = request.POST['target']
    op = request.POST['op']
    ids = copy.deepcopy(request.POST['ids'])
    ids = ids.replace('[', '').replace(']', '').replace(' ', '').split(',')

    try:
        for id in ids:
            _admin_actions_id(request, target, op, id)
    except actions.AdminActionNotPermitted:
        raise PermissionDenied

    redirect = reverse('admin-list', args=(target,))
    return HttpResponseRedirect(redirect)

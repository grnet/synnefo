# Copyright 2012 - 2014 GRNET S.A. All rights reserved.
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
import logging

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

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.functions import send_plain as send_email

# Import model-specific views
from synnefo_admin.admin import users as user_views
from synnefo_admin.admin import projects as project_views
from synnefo_admin.admin import vms as vm_views
from synnefo_admin.admin import volumes as volume_views

# server actions specific imports
from synnefo.logic import servers as servers_backend
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
PERMITTED_GROUPS = getattr(settings, 'ADMIN_PERMITTED_GROUPS', ['admin'])
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
def json_list(request, type):
    """Return a class-based view based on the given type."""
    logging.info("Request for json. Type: %s", type)

    if type == 'user':
        return user_views.UserJSONView.as_view()(request)
    if type == 'project':
        return project_views.ProjectJSONView.as_view()(request)
    if type == 'vm':
        return vm_views.VMJSONView.as_view()(request)
    if type == 'volume':
        return volume_views.VolumeJSONView.as_view()(request)
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
    else:
        logging.error("Wrong type: %s", type)
        # TODO: Return an error here
        return

    context.update(default_dict)
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
    else:
        logging.error("Wrong type: %s", type)
        # TODO: Return an error here
        return

    context.update(default_dict)

    return direct_to_template(request, template, extra_context=context)


def _admin_actions_id(request, target, op, id):
    if target == 'user':
        user_views.do_action(request, op, id)
    elif target == 'vm':
        vm_views.do_action(request, op, id)
    elif target == 'project':
        project_views.do_action(request, op, id)


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
        mail = request.POST['text']
    except:
        mail = None

    try:
        for id in ids:
            _admin_actions_id(request, target, op, id)
    except:
        logger.exception("admin_actions")

    redirect = reverse('admin-list', args=(target,))
    return HttpResponseRedirect(redirect)

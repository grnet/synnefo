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

# server actions specific imports
from synnefo.logic import servers as servers_backend
from synnefo.ui.views import UI_MEDIA_URL
import copy

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


@csrf_exempt
@admin_user_required
def details(request, type, id):
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


def index(request, type):
    """Admin-Interface main index view."""
    logging.info("Request for index. Type: %s", type)

    if type == 'user':
        context = user_views.index(request)
        template = user_views.templates['index']
    elif type == 'project':
        context = project_views.index(request)
        template = project_views.templates['index']
    elif type == 'vm':
        context = vm_views.index(request)
        template = vm_views.templates['index']
    else:
        logging.error("Wrong type: %s", type)
        # TODO: Return an error here
        return

    context.update(default_dict)

    return direct_to_template(request, template, extra_context=context)


@admin_user_required
@token_check
def vm_suspend(request, vm_id):
    vm = VirtualMachine.objects.get(pk=vm_id)
    vm.suspended = True
    vm.save()
    logging.info("VM %s suspended by %s", vm_id, request.user_uniq)
    account = vm.userid
    return HttpResponseRedirect(reverse('admin-details', args=(account,)))


@admin_user_required
@token_check
def vm_suspend_release(request, vm_id):
    vm = VirtualMachine.objects.get(pk=vm_id)
    vm.suspended = False
    vm.save()
    logging.info("VM %s unsuspended by %s", vm_id, request.user_uniq)
    account = vm.userid
    return HttpResponseRedirect(reverse('admin-details', args=(account,)))


@admin_user_required
@token_check
def vm_shutdown(request, vm_id):
    logging.info("VM %s shutdown by %s", vm_id, request.user_uniq)
    vm = VirtualMachine.objects.get(pk=vm_id)
    account = vm.userid
    error = None
    try:
        jobId = servers_backend.stop(vm)
    except Exception, e:
        error = e.message

    redirect = reverse('admin-details', args=(account,))
    if error:
        redirect = "%s?error=%s" % (redirect, error)
    return HttpResponseRedirect(redirect)


@admin_user_required
@token_check
def vm_start(request, vm_id):
    logging.info("VM %s start by %s", vm_id, request.user_uniq)
    vm = VirtualMachine.objects.get(pk=vm_id)
    account = vm.userid
    error = None
    try:
        jobId = servers_backend.start(vm)
    except Exception, e:
        error = e.message

    redirect = reverse('admin-details', args=(account,))
    if error:
        redirect = "%s?error=%s" % (redirect, error)
    return HttpResponseRedirect(redirect)


class AdminActionNotPermitted(Exception):

    """Exception when an action is not permitted."""

    pass


class AdminActionUnknown(Exception):

    """Exception when an action is unknown."""

    pass


def account_actions__(op, user, extra=None):
    logging.info("Op: %s, user: %s", op, user.email)
    if op == 'activate':
        if users.check_activate(user):
            users.activate(user)
        else:
            raise AdminActionNotPermitted
    elif op == 'deactivate':
        if users.check_deactivate(user):
            users.deactivate(user)
        else:
            raise AdminActionNotPermitted
    elif op == 'accept':
        if users.check_accept(user):
            users.accept(user)
        else:
            raise AdminActionNotPermitted
    elif op == 'reject':
        if users.check_reject(user):
            users.reject(user)
        else:
            raise AdminActionNotPermitted
    elif op == 'verify':
        if users.check_verify(user):
            users.verify(user)
        else:
            raise AdminActionNotPermitted
    elif op == 'contact':
        send_email(user, extra['mail'])
    else:
        raise AdminActionUnknown


@csrf_exempt
@admin_user_required
def account_actions(request, op, account):
    """Entry-point for operation on an account."""
    logging.info("Account action \"%s\" on %s started by %s",
                 op, account, request.user_uniq)

    if request.method == "POST":
        logging.info("POST body: %s", request.POST)
    redirect = reverse('admin-details', args=(account,))
    user = get_user(account)
    logging.info("I'm here!")

    # Try to get mail body, if any.
    try:
        mail = request.POST['text']
    except:
        mail = None

    try:
        account_actions__(op, user, extra={'mail': mail})
    except AdminActionNotPermitted:
        logging.info("Account action \"%s\" on %s is not permitted",
                     op, account)
        redirect = "%s?error=%s" % (redirect, "Action is not permitted")
    except AdminActionUnknown:
        logging.info("Unknown account action \"%s\"", op)
        redirect = "%s?error=%s" % (redirect, "Action is unknown")
    except:
        logger.exception("account_actions")

    return HttpResponseRedirect(redirect)


@csrf_exempt
def admin_actions(request):
    """Entry-point for all admin actions.

    Expects a JSON with the following fields: <TODO>
    """
    logging.info("Entered admin actions view")

    if request.method == "POST":
        logging.info("POST body: %s", request.POST)
    redirect = reverse('admin-index')

    resource = request.POST['resource']
    action = request.POST['type']
    ids = copy.deepcopy(request.POST['ids'])
    ids = ids.replace('[', '').replace(']', '').replace(' ', '').split(',')
    try:
        mail = request.POST['text']
    except:
        mail = None

    try:
        for id in ids:
            user = get_user(id)
            if resource == 'account':
                account_actions__(action, user, extra={'mail': mail})
            else:
                logging.warn("Not implemented yet.")
    except:
        logger.exception("admin_actions")

    return HttpResponseRedirect(redirect)

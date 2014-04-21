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
from astakos.logic import users
from astakos.im.functions import send_plain as send_email

# Get an activation backend for account actions
from astakos.im import activation_backends
abackend = activation_backends.get_backend()


# server actions specific imports
from synnefo.logic import servers as servers_backend
from synnefo.ui.views import UI_MEDIA_URL
import copy

logger = logging.getLogger(__name__)

ADMIN_MEDIA_URL = getattr(settings, 'ADMIN_MEDIA_URL',
                          settings.MEDIA_URL + 'admin/')

IP_SEARCH_REGEX = re.compile('([0-9]+)(?:\.[0-9]+){3}')
UUID_SEARCH_REGEX = re.compile('([0-9a-z]{8}-([0-9a-z]{4}-){3}[0-9a-z]{12})')
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


def get_user(query):
    """Get AstakosUser from query.

    The query can either be a user email or a UUID.
    """
    is_uuid = UUID_SEARCH_REGEX.match(query)

    try:
        if is_uuid:
            user = AstakosUser.objects.get(uuid=query)
        else:
            user = AstakosUser.objects.get(email=query)
    except ObjectDoesNotExist:
        logger.info("Failed to resolve '%s' into account" % query)
        return None

    return user


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
def account(request, search_query):
    """Account details view."""
    logging.info("Admin search by %s: %s", request.user_uniq, search_query)
    show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    error = request.GET.get('error', None)

    # By default we consider that the account exists
    account_exists = True

    # We may query the database for various stuff, so we will keep the original
    # query here.
    original_search_query = search_query

    account_name = ""
    account_email = ""
    account = ""
    vms = []
    networks = []
    is_ip = IP_SEARCH_REGEX.match(search_query)
    is_vm = VM_SEARCH_REGEX.match(search_query)

    if is_ip:
        # Search the IPAddressLog for the full use history of this IP
        return search_by_ip(request, search_query)
    elif is_vm:
        vmid = is_vm.groupdict().get('vmid')
        try:
            vm = VirtualMachine.objects.get(pk=int(vmid))
            search_query = vm.userid
        except ObjectDoesNotExist:
            account_exists = False
            account = None
            search_query = vmid

    if account_exists:
        user = get_user(search_query)
        if user:
            account = user.uuid
            account_email = user.email
            account_name = user.realname
        else:
            account_exists = False

    if account_exists:
        filter_extra = {}
        if not show_deleted:
            filter_extra['deleted'] = False

        # all user vms
        vms = VirtualMachine.objects.filter(
            userid=account, **filter_extra).order_by('deleted')
        # return all user private and public networks
        public_networks = Network.objects.filter(
            public=True, nics__machine__userid=account,
            **filter_extra).order_by('state').distinct()
        private_networks = Network.objects.filter(
            userid=account, **filter_extra).order_by('state')
        networks = list(public_networks) + list(private_networks)

    user_context = {
        'account_exists': account_exists,
        'error': error,
        'is_ip': is_ip,
        'is_vm': is_vm,
        'account': account,
        'search_query': original_search_query,
        'vms': vms,
        'show_deleted': show_deleted,
        'usermodel': user,
        'account_mail': account_email,
        'account_name': account_name,
        'account_accepted': user.is_active,
        'token': request.user['access']['token']['id'],
        'networks': networks,
        'available_ops': [
            'activate', 'deactivate', 'accept', 'reject', 'verify', 'contact'],
        'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
        'UI_MEDIA_URL': UI_MEDIA_URL
    }

    return direct_to_template(request, "admin/account.html",
                              extra_context=user_context)


def user_details(query):
    user = get_user(query)
    projects = ProjectMembership.objects.filter(person=user)
    vms = VirtualMachine.objects.filter(
        userid=user.uuid).order_by('deleted')

    context = {
        'main_item': user,
        'main_type': 'user',
        'associations_list': [
            (projects, 'project'),
            (vms, 'vm'),
        ]
    }
    return context


def vm_details(query):
    id = query.translate(None, 'vm-')
    vm = VirtualMachine.objects.get(pk=int(id))
    vms = VirtualMachine.objects.all
    context = {
        'main_item': vm,
        'main_type': 'vm',
        'associations_list': [(vms, 'vm')]
    }

    return context

details_dict = {
    'vm': {
        'fun': vm_details,
        'template': 'admin/vm_details.html',
    },
    'user': {
        'fun': user_details,
        'template': 'admin/user_details.html',
    },
}

default_dict = {
    'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
    'UI_MEDIA_URL': UI_MEDIA_URL,
}


@csrf_exempt
@admin_user_required
def details(request, type, id):
    logging.info("Request for details. Type: %s, ID: %s", type, id)
    try:
        fun = details_dict[type]['fun']
    except KeyError:
        logger.exception("Error in details")
        raise KeyError

    context = fun(str(id))
    context.update(default_dict)
    return direct_to_template(request, details_dict[type]['template'],
                              extra_context=context)


def create_vm_filters():
    state_values = [value for value, _ in VirtualMachine.OPER_STATES]

    filters = {}
    filters['state'] = {
        'name': 'State',
        'values': state_values,
    }
    return filters


def vm_index(request):
    context = {}
    context['filters'] = create_vm_filters()


def create_user_action_list():
    action_list = []
    action_list.append({
        'op': 'activate',
        'name': 'Activate a user',
        'resource': 'account'
    })
    action_list.append({
        'op': 'deactivate',
        'name': 'Deactivate',
        'resource': 'account'
    })
    action_list.append({
        'op': 'contact',
        'name': 'Send e-mail',
        'resource': 'account'
    })
    return action_list


def create_project_action_list():
    action_list = []
    action_list.append({
        'op': 'approve',
        'name': 'Approve project',
        'resource': 'project'
    })
    return action_list

def create_user_filters():
    filters = {}
    filters['state'] = {
        'name': 'State',
        'values': ['Active', 'Inactive', 'Pending Moderation',
                   'Pending Verification']
    }
    filters['enabled_providers'] = {
        'name': 'Providers',
        'values': ['Local', 'Shibboleth']
    }
    return filters


def user_index(request):
    context = {}
    context['filters'] = create_user_filters()
    context['action_list'] = create_user_action_list()

    ## if form submitted redirect to details
    #account = request.GET.get('account', None)
    #if account:
        #return redirect('admin-details',
                        #search_query=account)

    all = users.get_all()
    logging.info("These are the users %s", all)
    active = users.get_active().count()
    inactive = users.get_inactive().count()
    accepted = users.get_accepted().count()
    rejected = users.get_rejected().count()
    verified = users.get_verified().count()
    unverified = users.get_unverified().count()

    user_context = {
        'item_list': all,
        'item_type': 'user',
        'active': active,
        'inactive': inactive,
        'accepted': accepted,
        'rejected': rejected,
        'verified': verified,
        'unverified': unverified,
    }

    context.update(user_context)
    return context

def project_index(request):
    context = {}
    #context['filters'] = create_user_filters()
    context['action_list'] = create_project_action_list()

    ## if form submitted redirect to details
    #account = request.GET.get('account', None)
    #if account:
        #return redirect('admin-details',
                        #search_query=account)

    all = Project.objects.all()
    logging.info("These are the projects %s", all)

    project_context = {
        'item_list': all,
        'item_type': 'project',
    }

    context.update(project_context)
    return context

index_dict = {
    'user': {
        'fun': user_index,
        'template': 'admin/user_index.html',
    },
    'project': {
        'fun': project_index,
        'template': 'admin/project_index.html',
    },
    'vm': {
        'fun': vm_index,
        'template': 'admin/vm_index.html',
    },
}


def index(request, type):
    """Admin-Interface index view."""
    logging.info("Request for index. Type: %s", type)
    try:
        fun = index_dict[type]['fun']
    except KeyError:
        logger.exception("Error in details")
        raise KeyError

    context = fun(request)
    context.update(default_dict)
    logging.info("My item_list is %s", context['item_list'])
    return direct_to_template(request, index_dict[type]['template'],
                              extra_context=context)


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

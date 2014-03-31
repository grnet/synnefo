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
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt

from urllib import unquote

import astakosclient
from snf_django.lib import astakos

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser

# Get an activation backend for account actions
from astakos.im import activation_backends
abackend = activation_backends.get_backend()


# server actions specific imports
from synnefo.logic import servers as servers_backend
from synnefo.ui.views import UI_MEDIA_URL

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

@admin_user_required
def index(request):
    """
    Admin-Interface index view.
    """
    # if form submitted redirect to details
    account = request.GET.get('account', None)
    if account:
        return redirect('admin-details',
                        search_query=account)

    # show index template
    return direct_to_template(request, "admin/index.html",
                              extra_context={'ADMIN_MEDIA_URL':
                                             ADMIN_MEDIA_URL})


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
            account_accepted = user.moderated
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
        'user': user,
        'account_mail': account_email,
        'account_name': account_name,
        'account_accepted': user.is_active,
        'token': request.user['access']['token']['id'],
        'networks': networks,
        'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
        'UI_MEDIA_URL': UI_MEDIA_URL
    }

    return direct_to_template(request, "admin/account.html",
                              extra_context=user_context)


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


# TODO: do not introduce logic of your own
@csrf_exempt
@admin_user_required
def account_accept(request, account):
    """Function to accept an account."""
    logging.info("Account acceptance of  %s started by %s",
                 account, request.user_uniq)

    redirect = reverse('admin-details', args=(account,))
    user = get_user(account)

    if not user:
        redirect = "%s?error=%s" % (redirect, "Account does not exist")
        return HttpResponseRedirect(redirect)

    #abackend.handle_verification
    if not user.email_verified:
        user.email_verified = True
        user.save()

    #abackend.handle_moderation(user, accept=True)
    if not user.moderated:
        user.moderated = True
        user.save()

    if not user.is_active:
        user.is_active = True
        user.save()

    return HttpResponseRedirect(redirect)


# TODO: do not introduce logic of your own
@csrf_exempt
@admin_user_required
def account_reject(request, account):
    """Function to accept an account."""
    logging.info("Account rejection of  %s started by %s",
                 account, request.user_uniq)

    redirect = reverse('admin-details', args=(account,))
    user = get_user(account)

    if not user:
        redirect = "%s?error=%s" % (redirect, "Account does not exist")
        return HttpResponseRedirect(redirect)

    user.moderated = False
    abackend.deactivate_user(user)
    abackend.handle_moderation(user, accept=False)
    return HttpResponseRedirect(redirect)

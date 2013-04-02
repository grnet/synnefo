# Copyright 2012 GRNET S.A. All rights reserved.
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
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse

from urllib import unquote

from synnefo.lib.astakos import get_user
from synnefo.db.models import VirtualMachine, NetworkInterface, Network
from synnefo.lib import astakos

# server actions specific imports
from synnefo.api import servers
from synnefo.logic import backend as servers_backend

logger = logging.getLogger(__name__)

IP_SEARCH_REGEX = re.compile('([0-9]+)(?:\.[0-9]+){3}')
UUID_SEARCH_REGEX = re.compile('([0-9a-z]{8}-([0-9a-z]{4}-){3}[0-9a-z]{12})')
VM_SEARCH_REGEX = re.compile('vm(-){0,}(?P<vmid>[0-9]+)')



def get_token_from_cookie(request, cookiename):
    """
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


AUTH_COOKIE_NAME = getattr(settings, 'HELPDESK_AUTH_COOKIE_NAME',
                           getattr(settings, 'UI_AUTH_COOKIE_NAME',
                                   '_pithos2_a'))
PERMITTED_GROUPS = getattr(settings, 'HELPDESK_PERMITTED_GROUPS', ['helpdesk'])
SHOW_DELETED_VMS = getattr(settings, 'HELPDESK_SHOW_DELETED_VMS', False)

# guess cyclades setting too
USER_CATALOG_URL = getattr(settings, 'CYCLADES_USER_CATALOG_URL', None)
USER_CATALOG_URL = getattr(settings, 'HELPDESK_USER_CATALOG_URL',
                           USER_CATALOG_URL)


def token_check(func):
    """
    Mimic csrf security check using user auth token.
    """
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user'):
            raise PermissionDenied

        token = request.POST.get('token', None)
        if token and token == request.user.get('auth_token', None):
            return func(request, *args, **kwargs)

        raise PermissionDenied

    return wrapper


def helpdesk_user_required(func, permitted_groups=PERMITTED_GROUPS):
    """
    Django view wrapper that checks if identified request user has helpdesk
    permissions (exists in helpdesk group)
    """
    def wrapper(request, *args, **kwargs):
        HELPDESK_ENABLED = getattr(settings, 'HELPDESK_ENABLED', True)
        if not HELPDESK_ENABLED:
            raise Http404

        token = get_token_from_cookie(request, AUTH_COOKIE_NAME)
        get_user(request, settings.ASTAKOS_URL, fallback_token=token)
        if hasattr(request, 'user') and request.user:
            groups = request.user.get('groups', [])

            if not groups:
                logger.error("Failed to access helpdesk view %r",
                             request.user_uniq)
                raise PermissionDenied

            has_perm = False
            for g in groups:
                if g in permitted_groups:
                    has_perm = True

            if not has_perm:
                logger.error("Failed to access helpdesk view %r. No valid "
                             "helpdesk group (%r) matches user groups (%r)",
                             request.user_uniq, permitted_groups, groups)
                raise PermissionDenied
        else:
            logger.error("Failed to access helpdesk view %r. No authenticated "
                         "user found.")
            raise PermissionDenied

        logging.info("User %s accessed helpdesk view (%s)", request.user_uniq,
                     request.path)
        return func(request, *args, **kwargs)

    return wrapper


@helpdesk_user_required
def index(request):
    """
    Helpdesk index view.
    """
    # if form submitted redirect to details
    account = request.GET.get('account', None)
    if account:
        return redirect('synnefo.helpdesk.views.account',
                        search_query=account)

    # show index template
    return direct_to_template(request, "helpdesk/index.html")


@helpdesk_user_required
def account(request, search_query):
    """
    Account details view.
    """

    logging.info("Helpdesk search by %s: %s", request.user_uniq, search_query)
    show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))

    account_exists = True
    vms = []
    networks = []
    is_ip = IP_SEARCH_REGEX.match(search_query)
    is_uuid = UUID_SEARCH_REGEX.match(search_query)
    is_vm = VM_SEARCH_REGEX.match(search_query)
    account_name = search_query
    auth_token = request.user.get('auth_token')

    if is_ip:
        try:
            nic = NetworkInterface.objects.get(ipv4=search_query)
            search_query = nic.machine.userid
            is_uuid = True
        except NetworkInterface.DoesNotExist:
            account_exists = False
            account = None

    if is_vm:
        vmid = is_vm.groupdict().get('vmid')
        try:
            vm = VirtualMachine.objects.get(pk=int(vmid))
            search_query = vm.userid
            is_uuid = True
        except VirtualMachine.DoesNotExist:
            account_exists = False
            account = None
            search_query = vmid

    if is_uuid:
        account = search_query
        account_name = astakos.get_displayname(auth_token, account,
                                               USER_CATALOG_URL)

    if account_exists and not is_uuid:
        account_name = search_query
        account = astakos.get_user_uuid(auth_token, account_name,
                                        USER_CATALOG_URL)

    if not account:
        account_exists = False

    filter_extra = {}
    if not show_deleted:
        filter_extra['deleted'] = False

    # all user vms
    vms = VirtualMachine.objects.filter(userid=account,
                                        **filter_extra).order_by('deleted')
    # return all user private and public networks
    public_networks = Network.objects.filter(public=True,
                                             nics__machine__userid=account,
                                             **filter_extra
                                             ).order_by('state').distinct()
    private_networks = Network.objects.filter(userid=account,
                                              **filter_extra).order_by('state')
    networks = list(public_networks) + list(private_networks)

    if vms.count() == 0 and private_networks.count() == 0:
        account_exists = False

    user_context = {
        'account_exists': account_exists,
        'is_ip': is_ip,
        'is_vm': is_vm,
        'is_uuid': is_uuid,
        'account': account,
        'search_query': search_query,
        'vms': vms,
        'show_deleted': show_deleted,
        'account_name': account_name,
        'token': request.user['auth_token'],
        'networks': networks,
        'UI_MEDIA_URL': settings.UI_MEDIA_URL
    }

    return direct_to_template(request, "helpdesk/account.html",
                              extra_context=user_context)


@helpdesk_user_required
@token_check
def vm_suspend(request, vm_id):
    vm = VirtualMachine.objects.get(pk=vm_id)
    vm.suspended = True
    vm.save()
    logging.info("VM %s suspended by %s", vm_id, request.user_uniq)
    account = vm.userid
    return HttpResponseRedirect(reverse('helpdesk-details', args=(account,)))


@helpdesk_user_required
@token_check
def vm_suspend_release(request, vm_id):
    vm = VirtualMachine.objects.get(pk=vm_id)
    vm.suspended = False
    vm.save()
    logging.info("VM %s unsuspended by %s", vm_id, request.user_uniq)
    account = vm.userid
    return HttpResponseRedirect(reverse('helpdesk-details', args=(account,)))


@helpdesk_user_required
@token_check
def vm_shutdown(request, vm_id):
    logging.info("VM %s shutdown by %s", vm_id, request.user_uniq)
    vm = VirtualMachine.objects.get(pk=vm_id)
    servers.start_action(vm, 'STOP')
    servers_backend.shutdown_instance(vm)
    account = vm.userid
    return HttpResponseRedirect(reverse('helpdesk-details', args=(account,)))


@helpdesk_user_required
@token_check
def vm_start(request, vm_id):
    logging.info("VM %s start by %s", vm_id, request.user_uniq)
    vm = VirtualMachine.objects.get(pk=vm_id)
    servers.start_action(vm, 'START')
    servers_backend.startup_instance(vm)
    account = vm.userid
    return HttpResponseRedirect(reverse('helpdesk-details', args=(account,)))

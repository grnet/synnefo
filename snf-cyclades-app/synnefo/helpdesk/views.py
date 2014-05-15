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

from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse

from urllib import unquote

import astakosclient
from snf_django.lib import astakos

from synnefo.db.models import VirtualMachine, Network, IPAddressLog

# server actions specific imports
from synnefo.logic import servers as servers_backend
from synnefo.ui.views import UI_MEDIA_URL

logger = logging.getLogger(__name__)

HELPDESK_MEDIA_URL = getattr(settings, 'HELPDESK_MEDIA_URL',
                             settings.MEDIA_URL + 'helpdesk/')

IP_SEARCH_REGEX = re.compile('([0-9]+)(?:\.[0-9]+){3}')
IP_V6_SEARCH_REGEX = re.compile('^([0-9A-Fa-f]{0,4}:){2,7}'
                                '([0-9A-Fa-f]{1,4}$|'
                                '((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
                                '(\.|$)){4})$')

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
        astakos.get_user(request, settings.ASTAKOS_AUTH_URL,
                         fallback_token=token, logger=logger)
        if hasattr(request, 'user') and request.user:
            groups = request.user['access']['user']['roles']
            groups = [g["name"] for g in groups]

            if not groups:
                logger.info("Failed to access helpdesk view. User: %r",
                            request.user_uniq)
                raise PermissionDenied

            has_perm = False
            for g in groups:
                if g in permitted_groups:
                    has_perm = True

            if not has_perm:
                logger.info("Failed to access helpdesk view %r. No valid "
                            "helpdesk group (%r) matches user groups (%r)",
                            request.user_uniq, permitted_groups, groups)
                raise PermissionDenied
        else:
            logger.info("Failed to access helpdesk view %r. No authenticated "
                        "user found.", request.user_uniq)
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
        return redirect('helpdesk-details',
                        search_query=account)

    # show index template
    return direct_to_template(request, "helpdesk/index.html",
                              extra_context={'HELPDESK_MEDIA_URL':
                                             HELPDESK_MEDIA_URL})


@helpdesk_user_required
def account(request, search_query):
    """
    Account details view.
    """

    logging.info("Helpdesk search by %s: %s", request.user_uniq, search_query)
    show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    error = request.GET.get('error', None)

    account_exists = True
    # flag to indicate successfull astakos calls
    account_resolved = False
    vms = []
    networks = []
    is_ip = IP_SEARCH_REGEX.match(search_query) or \
            IP_V6_SEARCH_REGEX.match(search_query)
    is_uuid = UUID_SEARCH_REGEX.match(search_query)
    is_vm = VM_SEARCH_REGEX.match(search_query)
    account_name = search_query
    auth_token = request.user['access']['token']['id']

    if is_ip:
        # Search the IPAddressLog for the full use history of this IP
        return search_by_ip(request, search_query)

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

    astakos_client = astakosclient.AstakosClient(
        auth_token, settings.ASTAKOS_AUTH_URL,
        retry=2, use_pool=True, logger=logger)

    account = None
    if is_uuid:
        account = search_query
        try:
            account_name = astakos_client.get_username(account)
        except:
            logger.info("Failed to resolve '%s' into account" % account)

    if account_exists and not is_uuid:
        account_name = search_query
        try:
            account = astakos_client.get_uuid(account_name)
        except:
            logger.info("Failed to resolve '%s' into account" % account_name)

    if not account:
        account_exists = False
    else:
        account_resolved = True

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

    if vms.count() == 0 and private_networks.count() == 0 and not \
            account_resolved:
        account_exists = False

    user_context = {
        'account_exists': account_exists,
        'error': error,
        'is_ip': is_ip,
        'is_vm': is_vm,
        'is_uuid': is_uuid,
        'account': account,
        'search_query': search_query,
        'vms': vms,
        'show_deleted': show_deleted,
        'account_name': account_name,
        'token': request.user['access']['token']['id'],
        'networks': networks,
        'HELPDESK_MEDIA_URL': HELPDESK_MEDIA_URL,
        'UI_MEDIA_URL': UI_MEDIA_URL
    }

    return direct_to_template(request, "helpdesk/account.html",
                              extra_context=user_context)


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
        'is_ip': True,
        'ips': ips,
        'search_query': search_query,
        'token': auth_token,
        'HELPDESK_MEDIA_URL': HELPDESK_MEDIA_URL,
        'UI_MEDIA_URL': UI_MEDIA_URL
    }

    return direct_to_template(request, "helpdesk/ip.html",
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
    account = vm.userid
    error = None
    try:
        jobId = servers_backend.stop(vm)
    except Exception, e:
        error = e.message

    redirect = reverse('helpdesk-details', args=(account,))
    if error:
        redirect = "%s?error=%s" % (redirect, error)
    return HttpResponseRedirect(redirect)


@helpdesk_user_required
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

    redirect = reverse('helpdesk-details', args=(account,))
    if error:
        redirect = "%s?error=%s" % (redirect, error)
    return HttpResponseRedirect(redirect)

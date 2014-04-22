# Copyright 2014 GRNET S.A. All rights reserved.
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

import logging
import re
from astakos.logic import users
from actions import AdminAction
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project

from astakos.api.quotas import get_quota_usage

UUID_SEARCH_REGEX = re.compile('([0-9a-z]{8}-([0-9a-z]{4}-){3}[0-9a-z]{12})')
SHOW_DELETED_VMS = getattr(settings, 'ADMIN_SHOW_DELETED_VMS', False)

templates = {
    'index': 'admin/user_index.html',
    'details': 'admin/user_details.html',
}


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
        logging.info("Failed to resolve '%s' into account" % query)
        return None

    return user


def generate_actions():
    """Create a list of actions on users.

    The actions are: activate/deactivate, accept/reject, verify, contact.
    """
    actions = []

    action = AdminAction(op='activate', name='Activate',
                         target='user', severity='trivial',
                         allowed_groups='admin')
    actions.append(action)

    action = AdminAction(op='deactivate', name='Deactivate',
                         target='user', severity='trivial',
                         allowed_groups='admin')
    actions.append(action)

    action = AdminAction(op='accept', name='Accept',
                         target='user', severity='trivial',
                         allowed_groups='admin')
    actions.append(action)

    action = AdminAction(op='reject', name='Reject',
                         target='user', severity='irreversible',
                         allowed_groups='admin')
    actions.append(action)

    action = AdminAction(op='verify', name='Verify',
                         target='user', severity='trivial',
                         allowed_groups='admin')
    actions.append(action)

    action = AdminAction(op='contact', name='Send e-mail',
                         target='user', severity='trivial',
                         allowed_groups='admin')
    actions.append(action)
    return actions


def index(request):
    """Index view for Astakos users."""
    context = {}
    context['action_list'] = generate_actions()

    all = users.get_all()
    logging.info("These are the users %s", all)

    user_context = {
        'item_list': all,
        'item_type': 'user',
    }

    context.update(user_context)
    return context


def get_quotas(user):
    """Transform the usage dictionary, as retrieved from api.quotas.

    Return a list of dictionaries that represent the quotas of the user. Each
    dictionary has the following form:

    {
        'project': <Project instance>,
        'resources': [('Resource Name1', <Resource dict>),
                      ('Resource Name2', <Resource dict>),...]
    }

    where 'Resource Name' is the name of the resource and <Resource dict> is
    the dictionary that is returned by get_quota_usage and has the following
    fields:

        pending, project_pending, project_limit, project_usage, usage.

    Note, the get_quota_usage function returns many
    dicts, but we only keep the ones that have project_limit > 0
    """
    usage = get_quota_usage(user)

    quotas = []
    for project_id, resource_dict in usage.iteritems():
        source = {}
        source['project'] = Project.objects.get(uuid=project_id)
        q_res = source['resources'] = []

        for resource_name, resource in resource_dict.iteritems():
            if resource['project_limit'] == 0:
                continue
            else:
                q_res.append((resource_name, resource))

        quotas.append(source)

    return quotas


def details(request, query):
    """Details view for Astakos users."""
    error = request.GET.get('error', None)

    user = get_user(query)
    quotas = get_quotas(user)

    project_memberships = ProjectMembership.objects.filter(person=user)
    projects = map(lambda p: p.project, project_memberships)

    vms = VirtualMachine.objects.filter(
        userid=user.uuid).order_by('deleted')

    filter_extra = {}
    show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    if not show_deleted:
        filter_extra['deleted'] = False

    public_networks = Network.objects.filter(
        public=True, nics__machine__userid=user.uuid,
        **filter_extra).order_by('state').distinct()
    private_networks = Network.objects.filter(
        userid=user.uuid, **filter_extra).order_by('state')
    networks = list(public_networks) + list(private_networks)
    logging.info("Networks are: %s", networks)

    context = {
        'main_item': user,
        'main_type': 'user',
        'associations_list': [
            (quotas, 'quota'),
            (projects, 'project'),
            (vms, 'vm'),
            (networks, 'network'),
        ]
    }

    return context

# DEPRECATED
#@admin_user_required
#def account(request, search_query):
    #"""Account details view."""
    #logging.info("Admin search by %s: %s", request.user_uniq, search_query)
    #show_deleted = bool(int(request.GET.get('deleted', SHOW_DELETED_VMS)))
    #error = request.GET.get('error', None)

    ## By default we consider that the account exists
    #account_exists = True

    ## We may query the database for various stuff, so we will keep the original
    ## query here.
    #original_search_query = search_query

    #account_name = ""
    #account_email = ""
    #account = ""
    #vms = []
    #networks = []
    #is_ip = IP_SEARCH_REGEX.match(search_query)
    #is_vm = VM_SEARCH_REGEX.match(search_query)

    #if is_ip:
        ## Search the IPAddressLog for the full use history of this IP
        #return search_by_ip(request, search_query)
    #elif is_vm:
        #vmid = is_vm.groupdict().get('vmid')
        #try:
            #vm = VirtualMachine.objects.get(pk=int(vmid))
            #search_query = vm.userid
        #except ObjectDoesNotExist:
            #account_exists = False
            #account = None
            #search_query = vmid

    #if account_exists:
        #user = get_user(search_query)
        #if user:
            #account = user.uuid
            #account_email = user.email
            #account_name = user.realname
        #else:
            #account_exists = False

    #if account_exists:
        #filter_extra = {}
        #if not show_deleted:
            #filter_extra['deleted'] = False

        ## all user vms
        #vms = VirtualMachine.objects.filter(
            #userid=account, **filter_extra).order_by('deleted')
        ## return all user private and public networks
        #public_networks = Network.objects.filter(
            #public=True, nics__machine__userid=account,
            #**filter_extra).order_by('state').distinct()
        #private_networks = Network.objects.filter(
            #userid=account, **filter_extra).order_by('state')
        #networks = list(public_networks) + list(private_networks)

    #user_context = {
        #'account_exists': account_exists,
        #'error': error,
        #'is_ip': is_ip,
        #'is_vm': is_vm,
        #'account': account,
        #'search_query': original_search_query,
        #'vms': vms,
        #'show_deleted': show_deleted,
        #'usermodel': user,
        #'account_mail': account_email,
        #'account_name': account_name,
        #'account_accepted': user.is_active,
        #'token': request.user['access']['token']['id'],
        #'networks': networks,
        #'available_ops': [
            #'activate', 'deactivate', 'accept', 'reject', 'verify', 'contact'],
        #'ADMIN_MEDIA_URL': ADMIN_MEDIA_URL,
        #'UI_MEDIA_URL': UI_MEDIA_URL
    #}

    #return direct_to_template(request, "admin/account.html",
                              #extra_context=user_context)

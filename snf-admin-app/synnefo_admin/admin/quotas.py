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
from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import VirtualMachine, Network
from astakos.im.user_utils import send_plain as send_email
from astakos.im.models import AstakosUser, Project
from astakos.im.functions import approve_application

from eztables.views import DatatablesView
from actions import (AdminAction, AdminActionUnknown, AdminActionNotPermitted,
                     noop)

templates = {
    'list': 'admin/quota_list.html',
    'details': 'admin/project_details.html',
}


def get_project(query):
    try:
        project = Project.objects.get(id=query)
    except Exception:
        project = Project.objects.get(uuid=query)
    return project


def get_allowed_actions(project):
    """Get a list of actions that can apply to a project."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        if action.can_apply(project):
            allowed_actions.append(key)

    return allowed_actions


def get_contact_mail(inst):
    members = inst.members.all()
    if members:
        return members[0].email


def get_contact_name(inst):
    members = inst.members.all()
    if members:
        return members[0].realname


def get_contact_id(inst):
    members = inst.members.all()
    if members:
        return members[0].uuid


class ProjectJSONView(DatatablesView):
    model = Project
    fields = ('id', 'id', 'realname',)

    extra = True

    def get_queryset(self):
        qs = super(ProjectJSONView, self).get_queryset()
        return qs.filter(is_base=True)

    def get_extra_data_row(self, inst):
        extra_dict = {
            'allowed_actions': {
                'display_name': "",
                'value': get_allowed_actions(inst),
                'visible': False,
            }, 'id': {
                'display_name': "ID",
                'value': inst.id,
                'visible': False,
            }, 'item_name': {
                'display_name': "Name",
                'value': inst.name,
                'visible': False,
            }, 'details_url': {
                'display_name': "Details",
                'value': reverse('admin-details', args=['project', inst.id]),
                'visible': True,
            }, 'contact_id': {
                'display_name': "Contact ID",
                'value': get_contact_id(inst),
                'visible': False,
            }, 'contact_mail': {
                'display_name': "Contact mail",
                'value': get_contact_mail(inst),
                'visible': True,
            }, 'contact_name': {
                'display_name': "Contact name",
                'value': get_contact_name(inst),
                'visible': True,
            }, 'uuid': {
                'display_name': "UUID",
                'value': inst.uuid,
                'visible': True,
            }, 'description': {
                'display_name': "Description",
                'value': inst.description,
                'visible': True,
            }
        }

        return extra_dict


class QuotaAction(AdminAction):

    """Class for actions on projects. Derived from AdminAction.

    Pre-determined Attributes:
        target:        project
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='project', f=f, **kwargs)


def generate_actions():
    """Create a list of actions on projects.

    The actions are: approve/deny, suspend/unsuspend, terminate/reinstate,
                     contact
    """
    actions = OrderedDict()

    actions['suspend'] = QuotaAction(name='Suspend', f=noop,)

    actions['unsuspend'] = QuotaAction(name='Release suspension', f=noop)

    actions['contact'] = QuotaAction(name='Send e-mail', f=noop)

    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    project = get_project(id)
    actions = generate_actions()
    logging.info("Op: %s, project: %s, function %s", op, project.uuid,
                 actions[op].f)

    if op == 'contact':
        if project.is_base:
            user = project.members.all()[0]
        else:
            user = project.owner
        actions[op].f(user, request.POST['text'])
    elif op == 'approve':
        actions[op].f(project.last_application.id)
    else:
        actions[op].f(project)


def catalog(request):
    """List view for Cyclades projects."""
    context = {}
    context['action_dict'] = generate_actions()
    context['columns'] = ["Column 1", "ID", "Name", "Details", "Summary"]
    context['item_type'] = 'quota'

    return context


def details(request, query):
    """Details view for Astakos projects."""
    project = get_project(query)

    users = project.members.all()
    vms = VirtualMachine.objects.filter(project=project.uuid)
    networks = Network.objects.filter(project=project.uuid)

    context = {
        'main_item': project,
        'main_type': 'project',
        'associations_list': [
            (users, 'user'),
            (vms, 'vm'),
            (networks, 'network'),
        ]
    }

    return context

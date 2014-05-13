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
from collections import OrderedDict

from actions import AdminAction, nop

from synnefo.db.models import VirtualMachine, Network, IPAddressLog
from astakos.im.models import AstakosUser, ProjectMembership, Project
from astakos.im.functions import approve_application

templates = {
    'list': 'admin/project_list.html',
    'details': 'admin/project_details.html',
}


def get_project(query):
    try:
        project = Project.objects.get(id=query)
    except Exception:
        project = Project.objects.get(uuid=query)
    return project

class ProjectAction(AdminAction):

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

    actions['approve'] = ProjectAction(name='Approve', f=approve_application,
                                       severity='trivial')

    actions['deny'] = ProjectAction(name='Deny', f=nop, severity='trivial')

    actions['suspend'] = ProjectAction(name='Suspend', f=nop,
                                       severity='trivial')

    actions['unsuspend'] = ProjectAction(name='Release suspension', f=nop,
                                         severity='trivial')

    actions['terminate'] = ProjectAction(name='Terminate', f=nop,
                                         severity='trivial')

    actions['reinstate'] = ProjectAction(name='Reinstate', f=nop,
                                         severity='trivial')

    actions['contact'] = ProjectAction(name='Send e-mail', f=nop,
                                       severity='trivial')

    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    project = get_project(id)
    actions = generate_actions()
    logging.info("Op: %s, project: %s, function", op, project.uuid,
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


def list(request):
    """List view for Astakos projects."""
    context = {}
    context['action_dict'] = generate_actions()

    all = Project.objects.all()
    logging.info("These are the projects %s", all)

    project_context = {
        'item_list': all,
        'item_type': 'project',
    }

    context.update(project_context)
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


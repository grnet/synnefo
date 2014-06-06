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
from operator import itemgetter

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse

from synnefo.db.models import (VirtualMachine, Network, Volume,
                               NetworkInterface, IPAddress)
from astakos.im.models import (AstakosUser, Project, ProjectResourceGrant,
                               Resource)

from eztables.views import DatatablesView
from actions import (AdminAction, AdminActionUnknown, AdminActionNotPermitted,
                     noop)
from astakos.im.user_utils import send_plain as send_email
from astakos.im.functions import (validate_project_action, ProjectConflict,
                                  approve_application, deny_application,
                                  suspend, unsuspend, terminate, reinstate)
from astakos.im.quotas import get_project_quota

from synnefo.util import units

import django_filters
from django.db.models import Q

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


def get_status_choices():
    ((value.upper(), '_') for value in Project.O_STATE_DISLAY.itervalues())


def filter_status(queryset, choices):
    choices = choices or ()
    if len(choices) == len(get_status_choices()):
        return queryset
    q = Q()
    logging.info("Choices: %s", choices)
    for c in choices:
        status = getattr(Project, 'O_%s' % c.upper())
        q |= Q(last_application__state=status) | Q(state=status)
        logging.info("q: %s", q)
    return queryset.filter(q).distinct()


class ProjectFilterSet(django_filters.FilterSet):

    """A collection of filters for Projects.

    This filter collection is based on django-filter's FilterSet.
    """

    realname = django_filters.CharFilter(label='Name', lookup_type='icontains')
    uuid = django_filters.CharFilter(label='UUID', lookup_type='icontains')
    description = django_filters.CharFilter(label='Description',
                                            lookup_type='icontains')
    #status = django_filters.MultipleChoiceFilter(
        #label='Status', action=filter_status, choices=get_status_choices)

    class Meta:
        model = Project
        fields = ('id', 'uuid', 'realname', 'description')


def get_allowed_actions(project):
    """Get a list of actions that can apply to a project."""
    allowed_actions = []
    actions = generate_actions()

    for key, action in actions.iteritems():
        try:
            if action.can_apply(project):
                allowed_actions.append(key)
        except ProjectConflict:
            pass

    return allowed_actions


def get_contact_mail(inst):
    if inst.owner:
        return inst.owner.email,


def get_contact_name(inst):
    if inst.owner:
        return inst.owner.realname,


def get_contact_id(inst):
    if inst.owner:
        return inst.owner.uuid


def is_resource_useful(resource, project_limit):
    """Simple function to check if the resource is useful to show.

    Values that have infinite or zero limits are discarded.
    """
    displayed_limit = units.show(project_limit, resource.unit)
    if not resource.uplimit or displayed_limit == 'inf':
        return False
    return True


def display_project_stats(inst, stat):
    """Display the requested project stats in a one-line string.

    Accepted stats are: 'project_limit', 'project_pending', 'project_usage'.
    Note that the output is sanitized, meaning that stats that correspond
    to infinite or zero limits will not be shown.
    """
    resource_list = []
    quota_dict = get_project_quota(inst)

    for resource_name, stats in quota_dict.iteritems():
        resource = Resource.objects.get(name=resource_name)
        if not is_resource_useful(resource, stats['project_limit']):
            continue
        value = units.show(stats[stat], resource.unit)
        resource_list.append((resource.display_name, value))

    resource_list = sorted(resource_list, key=itemgetter(0))
    if not resource_list:
        return "-"
    return ', '.join((': '.join(pair) for pair in resource_list))


def display_project_resources(inst, type):
    """Display project resources (member of total) in one line."""
    resource_list = []
    prqs = inst.resource_set

    for prq in prqs:
        r = prq.resource

        # Check the project limit to verify that we can print this resource
        if not is_resource_useful(r, prq.project_capacity):
            continue

        # Get human-readable (resource name, member capacity) tuple
        if type == 'member':
            resource_list.append((r.display_name,
                                  prq.display_member_capacity()))
        # Get human-readable (resource name, total capacity) tuple
        elif type == 'total':
            resource_list.append((r.display_name,
                                  prq.display_project_capacity()))
        else:
            raise Exception("Wrong type")

    resource_list = sorted(resource_list, key=itemgetter(0))
    return ', '.join((': '.join(pair) for pair in resource_list))


class ProjectJSONView(DatatablesView):
    model = Project
    fields = ('id', 'id', 'realname', 'state', 'creation_date', 'end_date')

    extra = True
    filters = ProjectFilterSet

    def format_data_row(self, row):
        row[3] = (str(row[3]) + ' (' +
                  Project.objects.get(id=row[0]).state_display() + ')')
        row[4] = str(row[4].date())
        row[5] = str(row[5].date())
        return row

    def get_extra_data_row(self, inst):
        extra_dict = OrderedDict()
        extra_dict['allowed_actions'] = {
            'display_name': "",
            'value': get_allowed_actions(inst),
            'visible': False,
        }
        extra_dict['id'] = {
            'display_name': "ID",
            'value': inst.id,
            'visible': False,
        }
        extra_dict['item_name'] = {
            'display_name': "Name",
            'value': inst.realname,
            'visible': False,
        }
        extra_dict['details_url'] = {
            'display_name': "Details",
            'value': reverse('admin-details', args=['project', inst.id]),
            'visible': True,
        }
        extra_dict['contact_id'] = {
            'display_name': "Contact ID",
            'value': get_contact_id(inst),
            'visible': False,
        }
        extra_dict['contact_mail'] = {
            'display_name': "Contact mail",
            'value': get_contact_mail(inst),
            'visible': False,
        }
        extra_dict['contact_name'] = {
            'display_name': "Contact name",
            'value': get_contact_name(inst),
            'visible': False,
        }
        extra_dict['uuid'] = {
            'display_name': "UUID",
            'value': inst.uuid,
            'visible': False,
        }

        if not inst.is_base:
            extra_dict['homepage'] = {
                'display_name': "Homepage",
                'value': inst.homepage,
                'visible': True,
            }

            extra_dict['description'] = {
                'display_name': "Description",
                'value': inst.description,
                'visible': True,
            }
            extra_dict['members'] = {
                'display_name': "Members",
                'value': (str(inst.members_count()) + ' / ' +
                          str(inst.limit_on_members_number)),
                'visible': True,
            }

            if inst.last_application.comments:
                extra_dict['comments'] = {
                    'display_name': "Comments for review",
                    'value': inst.last_application.comments,
                    'visible': True,
                }

            extra_dict['member_resources'] = {
                'display_name': "Member resource limits",
                'value': display_project_resources(inst, 'member'),
                'visible': True
            }

        extra_dict['limit'] = {
            'display_name': "Total resource limits",
            'value': display_project_resources(inst, 'total'),
            'visible': True,
        }
        extra_dict['usage'] = {
            'display_name': "Total resource usage",
            'value': display_project_stats(inst, 'project_usage'),
            'visible': True,
        }

        return extra_dict


class ProjectAction(AdminAction):

    """Class for actions on projects. Derived from AdminAction.

    Pre-determined Attributes:
    target:        project
    """

    def __init__(self, name, f, **kwargs):
        """Initialize the class with provided values."""
        AdminAction.__init__(self, name=name, target='project', f=f, **kwargs)


def check_project_action(action):
    return lambda p: validate_project_action(p, action)


def check_approve(project):
    if project.is_base:
        return False
    return project.last_application.can_approve()


def check_deny(project):
    if project.is_base:
        return False
    return project.last_application.can_deny()


def generate_actions():
    """Create a list of actions on projects.

    The actions are: approve/deny, suspend/unsuspend, terminate/reinstate,
    contact
    """
    actions = OrderedDict()

    actions['approve'] = ProjectAction(name='Approve', f=approve_application,
                                       c=check_approve,)

    actions['deny'] = ProjectAction(name='Deny', f=deny_application,
                                    c=check_deny,)

    actions['suspend'] = ProjectAction(name='Suspend', f=suspend,
                                       c=check_project_action("SUSPEND"),)

    actions['unsuspend'] = ProjectAction(name='Release suspension',
                                         f=unsuspend,
                                         c=check_project_action("UNSUSPEND"),)

    actions['terminate'] = ProjectAction(name='Terminate', f=terminate,
                                         c=check_project_action("TERMINATE"),)

    actions['reinstate'] = ProjectAction(name='Reinstate', f=reinstate,
                                         c=check_project_action("REINSTATE"),)

    actions['contact'] = ProjectAction(name='Send e-mail', f=send_email,)

    return actions


def do_action(request, op, id):
    """Apply the requested action on the specified user."""
    project = get_project(id)
    actions = generate_actions()
    logging.info("Op: %s, project: %s, fun: %s", op, project.uuid,
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
    context['filter_dict'] = ProjectFilterSet().filters.itervalues()
    context['columns'] = ["Column 1", "ID", "Name", "Status", "Creation date",
                          "Expiration date", "Details", "Summary"]
    context['item_type'] = 'project'

    return context


def details(request, query):
    """Details view for Astakos projects."""
    project = get_project(query)

    user_list = project.members.all()
    vm_list = VirtualMachine.objects.filter(project=project.uuid)
    volume_list = Volume.objects.filter(project=project.uuid)
    network_list = Network.objects.filter(project=project.uuid)
    ip_list = IPAddress.objects.filter(project=project.uuid)

    context = {
        'main_item': project,
        'main_type': 'project',
        'associations_list': [
            (user_list, 'user'),
            (vm_list, 'vm'),
            (volume_list, 'volume'),
            (network_list, 'network'),
            (ip_list, 'ip'),
        ]
    }

    return context

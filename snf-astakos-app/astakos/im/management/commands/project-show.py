# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

from optparse import make_option
from django.core.management.base import CommandError

from synnefo.lib.ordereddict import OrderedDict
from snf_django.management.commands import SynnefoCommand
from snf_django.management import utils
from astakos.im.models import Chain, ProjectApplication
from ._common import show_resource_value, style_options, check_style


class Command(SynnefoCommand):
    args = "<id>"
    help = "Show details for project (or application) <id>"

    option_list = SynnefoCommand.option_list + (
        make_option('--app',
                    action='store_true',
                    dest='app',
                    default=False,
                    help="Show details of applications instead of projects"
                    ),
        make_option('--pending',
                    action='store_true',
                    dest='pending',
                    default=False,
                    help=("For a given project, show also pending "
                          "modifications (applications), if any")
                    ),
        make_option('--members',
                    action='store_true',
                    dest='members',
                    default=False,
                    help=("Show a list of project memberships")
                    ),
        make_option('--unit-style',
                    default='mb',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to mb") % style_options),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide project ID or name")

        self.unit_style = options['unit_style']
        check_style(self.unit_style)

        show_pending = bool(options['pending'])
        show_members = bool(options['members'])
        search_apps = options['app']
        self.output_format = options['output_format']

        id_ = args[0]
        try:
            id_ = int(id_)
        except ValueError:
            raise CommandError("id should be an integer value.")

        if search_apps:
            app = get_app(id_)
            self.print_app(app)
        else:
            state, project, app = get_chain_state(id_)
            self.print_project(state, project, app)
            if show_members and project is not None:
                self.stdout.write("\n")
                fields, labels = members_fields(project)
                self.pprint_table(fields, labels, title="Members")
            if show_pending and state in Chain.PENDING_STATES:
                self.stdout.write("\n")
                self.print_app(app)

    def pprint_dict(self, d, vertical=True):
        utils.pprint_table(self.stdout, [d.values()], d.keys(),
                           self.output_format, vertical=vertical)

    def pprint_table(self, tbl, labels, title=None):
        utils.pprint_table(self.stdout, tbl, labels,
                           self.output_format, title=title)

    def print_app(self, app):
        app_info = app_fields(app)
        self.pprint_dict(app_info)
        self.print_resources(app)

    def print_project(self, state, project, app):
        if project is None:
            self.print_app(app)
        else:
            self.pprint_dict(project_fields(state, project, app))
            self.print_resources(project.application)

    def print_resources(self, app):
        fields, labels = resource_fields(app, self.unit_style)
        if fields:
            self.stdout.write("\n")
            self.pprint_table(fields, labels, title="Resource limits")


def get_app(app_id):
    try:
        return ProjectApplication.objects.get(id=app_id)
    except ProjectApplication.DoesNotExist:
        raise CommandError("Application with id %s not found." % app_id)


def get_chain_state(project_id):
    try:
        chain = Chain.objects.get(chain=project_id)
        return chain.full_state()
    except Chain.DoesNotExist:
        raise CommandError("Project with id %s not found." % project_id)


def chain_fields(state, project, app):
    if project is not None:
        return project_fields(state, project, app)
    else:
        return app_fields(app)


def resource_fields(app, style):
    labels = ('name', 'description', 'max per member')
    policies = app.projectresourcegrant_set.all()
    collect = []
    for policy in policies:
        name = policy.resource.name
        desc = policy.resource.desc
        capacity = policy.member_capacity
        collect.append((name, desc,
                        show_resource_value(capacity, name, style)))
    return collect, labels


def app_fields(app):
    mem_limit = app.limit_on_members_number
    mem_limit_show = mem_limit if mem_limit is not None else "unlimited"

    d = OrderedDict([
        ('project id', app.chain),
        ('application id', app.id),
        ('name', app.name),
        ('status', app.state_display()),
        ('owner', app.owner),
        ('applicant', app.applicant),
        ('homepage', app.homepage),
        ('description', app.description),
        ('comments for review', app.comments),
        ('request issue date', app.issue_date),
        ('request start date', app.start_date),
        ('request end date', app.end_date),
        ('join policy', app.member_join_policy_display),
        ('leave policy', app.member_leave_policy_display),
        ('max members', mem_limit_show),
    ])

    return d


def project_fields(s, project, last_app):
    app = project.application

    d = OrderedDict([
        ('project id', project.id),
        ('application id', app.id),
        ('name', app.name),
        ('status', Chain.state_display(s)),
    ])
    if s in Chain.PENDING_STATES:
        d.update([('pending application', last_app.id)])

    d.update([('owner', app.owner),
              ('applicant', app.applicant),
              ('homepage', app.homepage),
              ('description', app.description),
              ('comments for review', app.comments),
              ('request issue date', app.issue_date),
              ('request start date', app.start_date),
              ('creation date', project.creation_date),
              ('request end date', app.end_date),
              ])

    deact_date = project.deactivation_date
    if deact_date is not None:
        d['deactivation date'] = deact_date

    mem_limit = app.limit_on_members_number
    mem_limit_show = mem_limit if mem_limit is not None else "unlimited"

    d.update([
            ('join policy', app.member_join_policy_display),
            ('leave policy', app.member_leave_policy_display),
            ('max members', mem_limit_show),
            ('total members', project.members_count()),
    ])

    return d


def members_fields(project):
    labels = ('member uuid', 'email', 'status')
    objs = project.projectmembership_set.select_related('person')
    memberships = objs.all().order_by('state', 'person__email')
    collect = []
    for m in memberships:
        user = m.person
        collect.append((user.uuid,
                       user.email,
                       m.state_display()))

    return collect, labels

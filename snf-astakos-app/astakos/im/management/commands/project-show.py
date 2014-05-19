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

from optparse import make_option

from synnefo.lib.ordereddict import OrderedDict
from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management import utils
from astakos.im.models import ProjectApplication, Project
from astakos.im import quotas
from ._common import show_resource_value, style_options, check_style
from synnefo.util import units


class Command(SynnefoCommand):
    args = "<id>"
    help = "Show details for project <id>"

    option_list = SynnefoCommand.option_list + (
        make_option('--pending-app',
                    action='store_true',
                    dest='pending',
                    default=False,
                    help=("For a given project, show also pending "
                          "application, if any")
                    ),
        make_option('--members',
                    action='store_true',
                    dest='members',
                    default=False,
                    help=("Show a list of project memberships")
                    ),
        make_option('--quota',
                    action='store_true',
                    dest='list_quotas',
                    default=False,
                    help="List project quota"),
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
        show_quota = bool(options['list_quotas'])
        self.output_format = options['output_format']

        id_ = args[0]
        if True:
            project = get_chain_state(id_)
            self.print_project(project, show_quota)
            if show_members and project is not None:
                self.stdout.write("\n")
                fields, labels = members_fields(project)
                self.pprint_table(fields, labels, title="Members")
            if show_pending:
                app = project.last_application
                if app and app.state == ProjectApplication.PENDING:
                    self.stdout.write("\n")
                    self.print_app(app)

    def pprint_dict(self, d, vertical=True, title=None):
        utils.pprint_table(self.stdout, [d.values()], d.keys(),
                           self.output_format, vertical=vertical, title=title)

    def pprint_table(self, tbl, labels, title=None):
        utils.pprint_table(self.stdout, tbl, labels,
                           self.output_format, title=title)

    def print_app(self, app):
        app_info = app_fields(app)
        self.pprint_dict(app_info, title="Pending Application")
        self.print_app_resources(app)

    def print_project(self, project, show_quota=False):
        self.pprint_dict(project_fields(project))
        quota = (quotas.get_project_quota(project)
                 if show_quota else None)
        self.print_resources(project, quota=quota)

    def print_resources(self, project, quota=None):
        policies = project.projectresourcequota_set.all()
        fields, labels = resource_fields(policies, quota, self.unit_style)
        if fields:
            self.stdout.write("\n")
            self.pprint_table(fields, labels, title="Resource limits")

    def print_app_resources(self, app):
        policies = app.projectresourcegrant_set.all()
        fields, labels = resource_fields(policies, None, self.unit_style)
        if fields:
            self.stdout.write("\n")
            self.pprint_table(fields, labels, title="Resource limits")


def get_chain_state(project_id):
    try:
        return Project.objects.get(uuid=project_id)
    except Project.DoesNotExist:
        raise CommandError("Project with id %s not found." % project_id)


def resource_fields(policies, quota, style):
    labels = ('name', 'max per member', 'max per project')
    if quota:
        labels += ('usage',)
    collect = []
    for policy in policies:
        name = policy.resource.name
        capacity = policy.member_capacity
        p_capacity = policy.project_capacity
        row = (name,
               show_resource_value(capacity, name, style),
               show_resource_value(p_capacity, name, style))
        if quota:
            r_quota = quota.get(name)
            usage = r_quota.get('project_usage')
            row += (show_resource_value(usage, name, style),)
        collect.append(row)
    return collect, labels


def app_fields(app):
    d = OrderedDict([
        ('project id', app.chain.uuid),
        ('application id', app.id),
        ('status', app.state_display()),
        ('applicant', app.applicant),
        ('comments for review', app.comments),
        ('request issue date', app.issue_date),
        ])
    if app.name:
        d['name'] = app.name
    if app.owner:
        d['owner'] = app.owner
    if app.homepage:
        d['homepage'] = app.homepage
    if app.description:
        d['description'] = app.description
    if app.start_date:
        d['request start date'] = app.start_date
    if app.end_date:
        d['request end date'] = app.end_date
    if app.member_join_policy:
        d['join policy'] = app.member_join_policy_display
    if app.member_leave_policy:
        d['leave policy'] = app.member_leave_policy_display
    if app.limit_on_members_number:
        d['max members'] = units.show(app.limit_on_members_number, None)

    return d


def project_fields(project):
    app = project.last_application
    pending_app = (app.id if app and app.state == app.PENDING
                   else None)

    d = OrderedDict([
        ('project id', project.uuid),
        ('name', project.realname),
        ('status', project.state_display()),
        ('pending_app', pending_app),
        ('owner', project.owner),
        ('homepage', project.homepage),
        ('description', project.description),
        ('creation date', project.creation_date),
        ('request end date', project.end_date),
        ])

    deact = project.last_deactivation()
    if deact is not None:
        d['deactivation date'] = deact.date

    d.update([
            ('join policy', project.member_join_policy_display),
            ('leave policy', project.member_leave_policy_display),
            ('max members', units.show(project.limit_on_members_number, None)),
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

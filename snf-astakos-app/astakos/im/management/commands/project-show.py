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
from synnefo.webproject.management.commands import SynnefoCommand
from synnefo.webproject.management import utils
from astakos.im.models import Chain, ProjectApplication


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
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide project ID or name")

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
            self.pprint_dict(app_info(id_))
        else:
            state, project, app = get_chain_state(id_)
            self.pprint_dict(chain_fields(state, project, app))
            if show_members and project is not None:
                self.stdout.write("\n")
                fields, labels = members_fields(project)
                self.pprint_table(fields, labels)
            if show_pending and state in Chain.PENDING_STATES:
                self.stdout.write("\n")
                self.pprint_dict(app_fields(app))

    def pprint_dict(self, d, vertical=True):
        utils.pprint_table(self.stdout, [d.values()], d.keys(),
                           self.output_format, vertical=vertical)

    def pprint_table(self, tbl, labels):
        utils.pprint_table(self.stdout, tbl, labels,
                           self.output_format)


def app_info(app_id):
    try:
        app = ProjectApplication.objects.get(id=app_id)
        return app_fields(app)
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
        ('resources', app.resource_policies),
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
            ('resources', app.resource_policies),
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

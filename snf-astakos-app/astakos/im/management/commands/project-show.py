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
from django.core.management.base import BaseCommand, CommandError

from synnefo.lib.ordereddict import OrderedDict
from astakos.im.models import ProjectApplication, Project

from ._common import format_bool, format_date


class Command(BaseCommand):
    args = "<id or name>"
    help = "Show project details"

    option_list = BaseCommand.option_list + (
        make_option('--app',
                    action='store_true',
                    dest='app',
                    default=False,
                    help="Show application details instead"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide ID or name")

        name_or_id = args[0]
        is_id = name_or_id.isdigit()
        if is_id:
            name_or_id = int(name_or_id)

        infolist = (app_info(name_or_id, is_id) if options['app']
                    else project_info(name_or_id, is_id))

        for info in infolist:
            self.show_info(info)

    def show_info(self, info):
        for key, val in info.items():
            line = '%s: %s\n' % (key.rjust(22), val)
            self.stdout.write(line.encode('utf8'))
        self.stdout.write('\n')


def app_fields(app):
    d = OrderedDict([
            ('application id', app.id),
            ('project id', app.chain),
            ('name', app.name),
            ('owner', app.owner),
            ('status', app.state_display()),
            ('homepage', app.homepage),
            ('description', app.description),
            ('issue date', format_date(app.issue_date)),
            ('start date', format_date(app.start_date)),
            ('end date', format_date(app.end_date)),
            ('comments', app.comments),
            ('resources', app.resource_policies),
            ('join policy', app.member_join_policy_display),
            ('leave policy', app.member_leave_policy_display),
            ('max members', app.limit_on_members_number),
            ])

    return d


def project_fields(project):
    app = project.application
    d = OrderedDict([
            ('project id', project.id),
            ('application id', app.id),
            ('name', project.name),
            ('owner', app.owner),
            ('status', project.state_display()),
            ('creation date', format_date(project.creation_date)),
            ])
    deact_date = project.deactivation_date
    if deact_date is not None:
        d['deactivation date'] = format_date(deact_date)

    d.update([
            ('homepage', app.homepage),
            ('description', app.description),
            ('resources', app.resource_policies),
            ('join policy', app.member_join_policy_display),
            ('leave policy', app.member_leave_policy_display),
            ('max members', app.limit_on_members_number),
            ('total members', project.members_count()),
            ])

    memberships = project.projectmembership_set
    accepted  = [str(m.person) for m in memberships.any_accepted()]
    requested = [str(m.person) for m in memberships.requested()]
    suspended = [str(m.person) for m in memberships.suspended()]

    if accepted:
        d['accepted members'] = ', '.join(accepted)

    if suspended:
        d['suspended members'] = ', '.join(suspended)

    if requested:
        d['membership requests'] = ', '.join(requested)

    return d


def app_info(name_or_id, is_id):
    try:
        apps = ([ProjectApplication.objects.get(id=name_or_id)]
                if is_id
                else ProjectApplication.objects.search_by_name(name_or_id))
        return [app_fields(app) for app in apps]
    except ProjectApplication.DoesNotExist:
            return []


def project_info(name_or_id, is_id):
    try:
        projects = ([Project.objects.get(id=name_or_id)]
                    if is_id
                    else Project.objects.search_by_name(name_or_id))
        return [project_fields(project) for project in projects]
    except Project.DoesNotExist:
        return []

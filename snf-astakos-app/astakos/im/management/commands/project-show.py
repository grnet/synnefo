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

from django.core.management.base import BaseCommand, CommandError

from astakos.im.models import ProjectApplication, Project

from ._common import format_bool, format_date


class Command(BaseCommand):
    args = "<user ID or email>"
    help = "Show user info"

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide a user ID or email")

        name_or_id = args[0]
        if name_or_id.isdigit():
            try:
                # check whether it is a project application id
                project_app = ProjectApplication.objects.get(id=int(name_or_id))
            except ProjectApplication.DoesNotExist:
                try:
                    # check whether it is a project id
                    project = Project.objects.get(id=int(name_or_id))
                    project_app = project.application
                except Project.DoesNotExist:
                    raise CommandError("Invalid id.")
            projects = (project_app,)
        else:
            projects = ProjectApplication.objects.search_by_name(name_or_id)
            if projects.count() == 0:
                msg = "No projects or project applications found"
                raise CommandError(msg)

        for app in projects:
            kv = {
                'id': app.id,
                'name': app.name,
                'homepage': app.homepage,
                'description': app.description,
                'issue date': format_date(app.issue_date),
                'start date': format_date(app.start_date),
                'end date': format_date(app.end_date),
                'comments': app.comments,
                'status': app.state_display(),
                'owner': app.owner,
                'max participants': app.limit_on_members_number,
                'join policy': app.member_join_policy_display,
                'leave policy': app.member_leave_policy_display,
                'resources': app.resource_policies
            }
            try:
                if app.project:
                    members = app.project.project_membership_set.all()
                    members = members.values_list('person__last_name', 'state')
                    kv['members'] = members 
            except:
                pass

            for key, val in sorted(kv.items()):
                line = '%s: %s\n' % (key.rjust(22), val)
                self.stdout.write(line.encode('utf8'))
            self.stdout.write('\n')

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

from snf_django.management.commands import ListCommand

from astakos.im.models import Project, ProjectApplication
from ._common import is_uuid


class Command(ListCommand):
    help = """List projects and project status.

    Project status can be one of:
      Uninitialized        an uninitialized project,
                           with no pending application

      Pending              an uninitialized project, pending review

      Active               an active project

      Denied               an uninitialized project, denied by the admin

      Dismissed            a denied project, dismissed by the applicant

      Cancelled            an uninitialized project, cancelled by the applicant

      Suspended            a project suspended by the admin;
                           it can later be resumed

      Terminated           a terminated project; its name can be claimed
                           by a new project

      Deleted              an uninitialized, deleted project"""

    object_class = Project
    select_related = ["last_application", "owner"]

    option_list = ListCommand.option_list + (
        make_option('--new',
                    action='store_true',
                    dest='new',
                    default=False,
                    help="List only new pending uninitialized projects"),
        make_option('--modified',
                    action='store_true',
                    dest='modified',
                    default=False,
                    help="List only projects with pending modification"),
        make_option('--pending',
                    action='store_true',
                    dest='pending',
                    default=False,
                    help=("Show only projects with a pending application "
                          "(equiv. --modified --new)")),
        make_option('--deleted',
                    action='store_true',
                    dest='deleted',
                    default=False,
                    help="Also show cancelled/terminated projects"),
        make_option('--base-projects',
                    action='store_true',
                    default=False,
                    help="Also show base projects"),
    )

    def get_owner(project):
        return project.owner.email if project.owner else None

    def get_status(project):
        return project.state_display()

    def get_pending_app(project):
        app = project.last_application
        return app.id if app and app.state == app.PENDING else ""

    FIELDS = {
        "id": ("uuid", "Project ID"),
        "name": ("realname", "Project Name"),
        "owner": (get_owner, "Project Owner"),
        "status": (get_status, "Project Status"),
        "pending_app": (get_pending_app,
                        "An application pending for the project"),
    }

    fields = ["id", "name", "owner", "status", "pending_app"]

    def handle_args(self, *args, **options):
        try:
            name_filter = self.filters.pop("name")
            self.filters["realname"] = name_filter
        except KeyError:
            pass

        try:
            owner_filter = self.filters.pop("owner")
            if owner_filter is not None:
                if is_uuid(owner_filter):
                    self.filters["owner__uuid"] = owner_filter
                else:
                    self.filters["owner__email"] = owner_filter
        except KeyError:
            pass

        if not options['deleted']:
            self.excludes["state__in"] = Project.SKIP_STATES

        if not options['base_projects']:
            self.excludes["is_base"] = True

        if options["pending"]:
            self.filter_pending()
        else:
            if options['new']:
                self.filter_pending()
                self.filters["state"] = Project.UNINITIALIZED
            if options['modified']:
                self.filter_pending()
                self.filters["state__in"] = Project.INITIALIZED_STATES

    def filter_pending(self):
        self.filters["last_application__state"] = ProjectApplication.PENDING

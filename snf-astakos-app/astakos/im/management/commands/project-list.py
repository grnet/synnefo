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

from snf_django.management.commands import SynnefoCommand, CommandError

from astakos.im.models import Project, ProjectApplication
from django.db.models import Q
from snf_django.management import utils
from ._common import is_uuid, is_email


class Command(SynnefoCommand):
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

    option_list = SynnefoCommand.option_list + (
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
                    help="Also so cancelled/terminated projects"),
        make_option('--name',
                    dest='name',
                    help='Filter projects by name'),
        make_option('--owner',
                    dest='owner',
                    help='Filter projects by owner\'s email or uuid'),
    )

    def handle(self, *args, **options):

        flt = Q()
        owner = options['owner']
        if owner:
            flt &= filter_by_owner(owner)

        name = options['name']
        if name:
            flt &= Q(realname=name)

        if not options['deleted']:
            flt &= ~Q(state__in=Project.SKIP_STATES)

        pending = Q(last_application__isnull=False,
                    last_application__state=ProjectApplication.PENDING)

        if options['pending']:
            flt &= pending
        else:
            if options['new']:
                flt &= pending & Q(state=Project.UNINITIALIZED)
            if options['modified']:
                flt &= pending & Q(state__in=Project.INITIALIZED_STATES)

        projects = Project.objects.\
            select_related("last_application", "owner").filter(flt)

        labels = ('ProjID', 'Name', 'Owner', 'Status', 'Pending AppID')

        info = project_info(projects)
        utils.pprint_table(self.stdout, info, labels,
                           options["output_format"])


def filter_by_owner(s):
    if is_email(s):
        return Q(owner__email=s)
    if is_uuid(s):
        return Q(owner__uuid=s)
    raise CommandError("Expecting either email or uuid.")


def project_info(projects):
    l = []
    for project in projects:
        status = project.state_display()
        app = project.last_application
        pending_appid = app.id if app and app.state == app.PENDING else ""

        t = (project.uuid,
             project.realname,
             project.owner.email if project.owner else None,
             status,
             pending_appid,
             )
        l.append(t)
    return l

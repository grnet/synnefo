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

from astakos.im.models import Project
from django.db.models import Q
from snf_django.management import utils
from ._common import is_uuid, is_email


class Command(SynnefoCommand):
    help = """
    List projects and project status.

    Project status can be one of:
      Pending              an application <AppId> for a new project

      Active               an active project

      Active - Pending     an active project with
                           a pending modification <AppId>

      Denied               an application for a new project,
                           denied by the admin

      Dismissed            a denied project, dismissed by the applicant

      Cancelled            an application for a new project,
                           cancelled by the applicant

      Suspended            a project suspended by the admin;
                           it can later be resumed

      Suspended - Pending  a suspended project with
                           a pending modification <AppId>

      Terminated           a terminated project; its name can be claimed
                           by a new project
"""

    option_list = SynnefoCommand.option_list + (
        make_option('--all',
                    action='store_true',
                    dest='all',
                    default=False,
                    help="List all projects (default)"),
        make_option('--new',
                    action='store_true',
                    dest='new',
                    default=False,
                    help="List only new project applications"),
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
        make_option('--skip',
                    action='store_true',
                    dest='skip',
                    default=False,
                    help="Skip cancelled and terminated projects"),
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
            flt &= filter_by_name(name)

        chains = Project.objects.all_with_pending(flt)

        if not options['all']:
            if options['skip']:
                pred = lambda c: (
                    c[0].overall_state() not in Project.SKIP_STATES
                    or c[1] is not None)
                chains = filter_preds([pred], chains)

            preds = []
            if options['new'] or options['pending']:
                preds.append(
                    lambda c: c[0].overall_state() == Project.O_PENDING)
            if options['modified'] or options['pending']:
                preds.append(
                    lambda c: c[0].overall_state() != Project.O_PENDING
                    and c[1] is not None)

            if preds:
                chains = filter_preds(preds, chains)

        labels = ('ProjID', 'Name', 'Owner', 'Email', 'Status',
                  'Pending AppID')

        info = chain_info(chains)
        utils.pprint_table(self.stdout, info, labels,
                           options["output_format"])


def filter_preds(preds, chains):
    return [c for c in chains
            if any(map(lambda f: f(c), preds))]


def filter_by_name(name):
    return Q(application__name=name)


def filter_by_owner(s):
    if is_email(s):
        return Q(application__owner__email=s)
    if is_uuid(s):
        return Q(application__owner__uuid=s)
    raise CommandError("Expecting either email or uuid.")


def chain_info(chains):
    l = []
    for project, pending_app in chains:
        status = project.state_display()
        pending_appid = pending_app.id if pending_app is not None else ""
        application = project.application

        t = (project.pk,
             application.name,
             application.owner.realname,
             application.owner.email,
             status,
             pending_appid,
             )
        l.append(t)
    return l

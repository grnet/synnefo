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
from astakos.im.models import Chain

from ._common import format_bool, format_date


class Command(BaseCommand):
    args = "<id or name>"
    help = "Show project details"

    option_list = BaseCommand.option_list + (
        make_option('--pending',
                    action='store_true',
                    dest='pending',
                    default=False,
                    help="Show pending modification too"),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("Please provide project ID or name")

        show_pending = bool(options['pending'])

        name_or_id = args[0]
        is_id = name_or_id.isdigit()
        if is_id:
            name_or_id = int(name_or_id)

        chains = get_chains(name_or_id, is_id)
        infolist = collect_info(chains, show_pending)

        # if not infolist:
        #     kind = 'project application' if search_application else 'project'
        #     field = 'id' if is_id else 'name'
        #     msg = "Unknown %s with %s '%s'" % (kind, field, name_or_id)
        #     raise CommandError(msg)

        for info in infolist:
            self.show_info(info)

    def show_info(self, info):
        for key, val in info.items():
            line = '%s: %s\n' % (key.rjust(22), val)
            self.stdout.write(line)
        self.stdout.write('\n')


def get_chains(name_or_id, is_id):
    if is_id:
        try:
            return [Chain.objects.get(chain=name_or_id)]
        except Chain.DoesNotExist:
            return []
    else:
        return Chain.objects.search_by_name(name_or_id)

def collect_info(chains, pending):
    states = [chain.full_state() for chain in chains]

    infolist = []
    for state in states:
        infolist += (chain_fields(state, pending))
    return infolist

def chain_fields((s, project, app), request=False):
    l = []
    if project:
        l = [project_fields(s, project, app)]
        if request and s in Chain.PENDING_STATES:
            l.append(app_fields(app))
    else:
        l = [app_fields(app)]
    return l

def app_fields(app):
    mem_limit = app.limit_on_members_number
    mem_limit_show = mem_limit if mem_limit is not None else "unlimited"

    d = OrderedDict([
            ('project id', app.chain),
            ('application id', app.id),
            ('name', app.name),
            ('status', app.state_display()),
            ('owner', app.owner),
            ('homepage', app.homepage),
            ('description', app.description),
            ('comments for review', app.comments),
            ('request issue date', format_date(app.issue_date)),
            ('request start date', format_date(app.start_date)),
            ('request end date', format_date(app.end_date)),
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
            ('name', project.name),
            ('status', Chain.state_display(s)),
            ])
    if s in Chain.PENDING_STATES:
        d.update([('pending application', last_app.id)])

    d.update([('owner', app.owner),
              ('homepage', app.homepage),
              ('description', app.description),
              ('comments for review', app.comments),
              ('request issue date', format_date(app.issue_date)),
              ('request start date', format_date(app.start_date)),
              ('creation date', format_date(project.creation_date)),
              ('request end date', format_date(app.end_date)),
              ])

    deact_date = project.deactivation_date
    if deact_date is not None:
        d['deactivation date'] = format_date(deact_date)

    mem_limit = app.limit_on_members_number
    mem_limit_show = mem_limit if mem_limit is not None else "unlimited"

    d.update([
            ('resources', app.resource_policies),
            ('join policy', app.member_join_policy_display),
            ('leave policy', app.member_leave_policy_display),
            ('max members', mem_limit_show),
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

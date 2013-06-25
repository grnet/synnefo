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

from synnefo.webproject.management.commands import SynnefoCommand, CommandError

from astakos.im.models import Chain
from synnefo.webproject.management import utils
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

        chain_dict = Chain.objects.all_full_state()

        if not options['all']:
            f_states = []
            if options['new']:
                f_states.append(Chain.PENDING)
            if options['modified']:
                f_states += Chain.MODIFICATION_STATES
            if options['pending']:
                f_states.append(Chain.PENDING)
                f_states += Chain.MODIFICATION_STATES
            if options['skip']:
                if not f_states:
                    f_states = Chain.RELEVANT_STATES

            if f_states:
                chain_dict = filter_by(in_states(f_states), chain_dict)

            name = options['name']
            if name:
                chain_dict = filter_by(is_name(name), chain_dict)

            owner = options['owner']
            if owner:
                chain_dict = filter_by(is_owner(owner), chain_dict)

        labels = ('ProjID', 'Name', 'Owner', 'Email', 'Status', 'AppID')

        info = chain_info(chain_dict)
        utils.pprint_table(self.stdout, info, labels,
                           options["output_format"])


def is_name(name):
    def f(state, project, app):
        n = project.application.name if project else app.name
        return name == n
    return f


def in_states(states):
    def f(state, project, app):
        return state in states
    return f


def is_owner(s):
    def f(state, project, app):
        owner = app.owner
        if is_email(s):
            return owner.email == s
        if is_uuid(s):
            return owner.uuid == s
        raise CommandError("Expecting either email or uuid.")
    return f


def filter_by(f, chain_dict):
    d = {}
    for chain, tpl in chain_dict.iteritems():
        if f(*tpl):
            d[chain] = tpl
    return d


def chain_info(chain_dict):
    l = []
    for chain, (state, project, app) in chain_dict.iteritems():
        status = Chain.state_display(state)
        if state in Chain.PENDING_STATES:
            appid = str(app.id)
        else:
            appid = ""

        t = (chain,
             project.application.name if project else app.name,
             app.owner.realname,
             app.owner.email,
             status,
             appid,
             )
        l.append(t)
    return l

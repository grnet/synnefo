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

from django.core.management.base import NoArgsCommand

from astakos.im.models import Chain
from ._common import format, shortened


class Command(NoArgsCommand):
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

    option_list = NoArgsCommand.option_list + (
        make_option('--all',
                    action='store_true',
                    dest='all',
                    default=False,
                    help="List all projects (default)"),
        make_option('--new',
                    action='store_true',
                    dest='new',
                    default=False,
                    help="List only new project requests"),
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
        make_option('--full',
                    action='store_true',
                    dest='full',
                    default=False,
                    help="Do not shorten long names"),
        make_option('-c',
                    action='store_true',
                    dest='csv',
                    default=False,
                    help="Use pipes to separate values"),
        )

    def handle_noargs(self, **options):
        allow_shorten = not options['full']
        csv = options['csv']

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
                chain_dict = filter_by_state(chain_dict, f_states)

        self.show(csv, allow_shorten, chain_dict)

    def show(self, csv, allow_shorten, chain_dict):
        labels = ('ProjID', 'Name', 'Applicant', 'Email', 'Status', 'AppID')
        columns = (7, 23, 20, 20, 17, 7)

        if not csv:
            line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')

        for info in chain_info(chain_dict):

            fields = [
                (info['projectid'], False),
                (info['name'], True),
                (info['applicant'], True),
                (info['email'], True),
                (info['status'], False),
                (info['appid'], False),
                ]

            fields = [(format(elem), flag) for (elem, flag) in fields]

            if csv:
                line = '|'.join(fields)
            else:
                output = []
                for (field, shorten), width in zip(fields, columns):
                    s = (shortened(field, width) if shorten and allow_shorten
                         else field)
                    s = s.rjust(width)
                    output.append(s)

                line = ' '.join(output)

            self.stdout.write(line + '\n')

def filter_by_state(chain_dict, states):
    d = {}
    for chain, (state, project, app) in chain_dict.iteritems():
        if state in states:
            d[chain] = (state, project, app)
    return d

def chain_info(chain_dict):
    l = []
    for chain, (state, project, app) in chain_dict.iteritems():
        status = Chain.state_display(state)
        if state in Chain.PENDING_STATES:
            appid = str(app.id)
        else:
            appid = ""

        d = {
            'projectid' : str(chain),
            'name'  : project.application.name if project else app.name,
            'applicant' : app.applicant.realname,
            'email' : app.applicant.email,
            'status': status,
            'appid' : appid,
            }
        l.append(d)
    return l

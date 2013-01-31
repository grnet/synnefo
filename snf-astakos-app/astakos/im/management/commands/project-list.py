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
from ._common import format_bool, shortened


class Command(NoArgsCommand):
    help = "List projects"

    option_list = NoArgsCommand.option_list + (
        make_option('-c',
                    action='store_true',
                    dest='csv',
                    default=False,
                    help="Use pipes to separate values"),
        make_option('--skip',
                    action='store_true',
                    dest='skip',
                    default=False,
                    help="Skip cancelled and terminated projects"),
    )

    def handle_noargs(self, **options):
        labels = ('ProjID', 'Name', 'Owner', 'Status', 'AppID')
        columns = (7, 23, 23, 20, 7)

        if not options['csv']:
            line = ' '.join(l.rjust(w) for l, w in zip(labels, columns))
            self.stdout.write(line + '\n')
            sep = '-' * len(line)
            self.stdout.write(sep + '\n')

        chain_dict = Chain.objects.all_full_state()
        if options['skip']:
            chain_dict = do_skip(chain_dict)

        for info in chain_info(chain_dict):

            fields = [
                (info['projectid'], False),
                (info['name'], True),
                (info['owner'], True),
                (info['status'], False),
                (info['appid'], False),
            ]

            if options['csv']:
                line = '|'.join(fields)
            else:
                output = []
                for (field, shorten), width in zip(fields, columns):
                    s = shortened(field, width) if shorten else field
                    s = s.rjust(width)
                    output.append(s)

                line = ' '.join(output)

            self.stdout.write(line + '\n')

def do_skip(chain_dict):
    d = {}
    for chain, (state, project, app) in chain_dict.iteritems():
        if state not in Chain.SKIP_STATES:
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
            'name'  : str(project.application.name if project else app.name),
            'owner' : app.owner.realname,
            'status': status,
            'appid' : appid,
            }
        l.append(d)
    return l

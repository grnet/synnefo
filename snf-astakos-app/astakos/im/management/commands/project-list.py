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

from astakos.im.models import Chain, Project
from synnefo.webproject.management.commands import ListCommand


def get_name(chain):
    try:
        p = Project.objects.get(pk=chain.pk)
    except Project.DoesNotExist:
        app = chain.last_application()
        return app.name
    else:
        return p.name


def get_owner_name(chain):
    return chain.last_application().owner.realname


def get_owner_email(chain):
    return chain.last_application().owner.email


def get_state(chain):
    try:
        p = Project.objects.get(pk=chain.pk)
    except Project.DoesNotExist:
        p = None
    app = chain.last_application()
    return chain.get_state(p, app)[0]


def get_state_display(chain):
    return Chain.state_display(get_state(chain))


def get_appid(chain):
    try:
        p = Project.objects.get(pk=chain.pk)
    except Project.DoesNotExist:
        p = None
    app = chain.last_application()
    state = chain.get_state(p, app)[0]
    if state in Chain.PENDING_STATES:
        return str(app.id)
    else:
        return ""


class Command(ListCommand):
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

    object_class = Chain

    FIELDS = {
        'ProjID': ('pk', 'The id of the project'),
        'Name': (get_name, 'The name of the project'),
        'Owner': (get_owner_name, 'The name of the project owner'),
        'Email': (get_owner_email, 'The email of the project owner'),
        'Status': (get_state_display, 'The status of the project'),
        'AppID': (get_appid, 'The project application identification'),
    }

    fields = ['ProjID', 'Name', 'Owner', 'Email', 'Status', 'AppID']

    option_list = ListCommand.option_list + (
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
        make_option('--full',
                    action='store_true',
                    dest='full',
                    default=False,
                    help="Do not shorten long names"),
    )

    def handle_db_objects(self, objects, **options):
        if options['all']:
            return

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
            map(objects.remove,
                filter(lambda o: get_state(o) not in f_states, objects))

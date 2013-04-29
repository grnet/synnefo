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

from django.core.management.base import NoArgsCommand, CommandError

from collections import namedtuple
from optparse import make_option
from sqlalchemy import func
from sqlalchemy.sql import select, and_, or_

from pithos.api.util import get_backend
from pithos.backends.modular import (
    CLUSTER_NORMAL, CLUSTER_HISTORY, CLUSTER_DELETED
)
clusters = (CLUSTER_NORMAL, CLUSTER_HISTORY, CLUSTER_DELETED)

Usage = namedtuple('Usage', ('node', 'path', 'size', 'cluster'))
GetQuota = namedtuple('GetQuota', ('entity', 'resource', 'key'))

class ResetHoldingPayload(namedtuple('ResetHoldingPayload', (
    'entity', 'resource', 'key', 'imported', 'exported', 'returned', 'released'
))):
    __slots__ = ()

    def __str__(self):
        return '%s: %s' % (self.entity, self.imported)


ENTITY_KEY = '1'

backend = get_backend()
table = {}
table['nodes'] = backend.node.nodes
table['versions'] = backend.node.versions
table['policy'] = backend.node.policy
conn = backend.node.conn

def _retrieve_user_nodes(users=()):
    s = select([table['nodes'].c.path, table['nodes'].c.node])
    s = s.where(and_(table['nodes'].c.node != 0,
                     table['nodes'].c.parent == 0))
    if users:
        s = s.where(table['nodes'].c.path.in_(users))
    return conn.execute(s).fetchall()

def _compute_usage(nodes):
    usage = []
    append = usage.append
    for path, node in nodes:
        select_children = select(
            [table['nodes'].c.node]).where(table['nodes'].c.parent == node)
        select_descendants = select([table['nodes'].c.node]).where(
            or_(table['nodes'].c.parent.in_(select_children),
                table['nodes'].c.node.in_(select_children)))
        s = select([table['versions'].c.cluster,
                    func.sum(table['versions'].c.size)])
        s = s.group_by(table['versions'].c.cluster)
        s = s.where(table['nodes'].c.node == table['versions'].c.node)
        s = s.where(table['nodes'].c.node.in_(select_descendants))
        s = s.where(table['versions'].c.cluster == CLUSTER_NORMAL)
        d2 = dict(conn.execute(s).fetchall())

        try:
            size = d2[CLUSTER_NORMAL]
        except KeyError:
            size = 0
        append(Usage(
            node=node,
            path=path,
            size=size,
            cluster=CLUSTER_NORMAL))
    return usage

def _get_quotaholder_usage(usage):
    payload = []
    append = payload.append
    [append(GetQuota(
        entity=item.path,
        resource='pithos+.diskspace',
        key=ENTITY_KEY
    )) for item in usage]

    result = backend.quotaholder.get_quota(
        context={}, clientkey='pithos', get_quota=payload
    )
    return dict((entity, imported - exported + returned - released) for (
        entity, resource, quantity, capacity, import_limit, export_limit,
        imported, exported, returned, released, flags
    ) in result)


def _prepare_reset_holding(usage, only_diverging=False):
    """Verify usage and set quotaholder user usage"""
    reset_holding = []
    append = reset_holding.append

    quotaholder_usage = {}
    if only_diverging:
        quotaholder_usage = _get_quotaholder_usage(usage)

    for item in(usage):
        if only_diverging and quotaholder_usage.get(item.path) == item.size:
            continue

        if item.cluster == CLUSTER_NORMAL:
            append(ResetHoldingPayload(
                    entity=item.path,
                    resource='pithos+.diskspace',
                    key=ENTITY_KEY,
                    imported=item.size,
                    exported=0,
                    returned=0,
                    released=0))
    return reset_holding


class Command(NoArgsCommand):
    help = "List and reset pithos usage"

    option_list = NoArgsCommand.option_list + (
        make_option('--list',
                    dest='list',
                    action="store_true",
                    default=True,
                    help="List usage for all or specified user"),
        make_option('--reset',
                    dest='reset',
                    action="store_true",
                    default=False,
                    help="Reset usage for all or specified users"),
        make_option('--diverging',
                    dest='diverging',
                    action="store_true",
                    default=False,
                    help=("List or reset diverging usages")),
        make_option('--user',
                    dest='users',
                    action='append',
                    metavar='USER_UUID',
                    help=("Specify which users --list or --reset applies."
                          "This option can be repeated several times."
                          "If no user is specified --list or --reset will be applied globally.")),
    )

    def handle_noargs(self, **options):
        try:
            user_nodes = _retrieve_user_nodes(options['users'])
            if not user_nodes:
                raise CommandError('No users found.')
            usage = _compute_usage(user_nodes)
            reset_holding = _prepare_reset_holding(
                usage, only_diverging=options['diverging']
            )

            if options['list']:
                print '\n'.join([str(i) for i in reset_holding])

            if options['reset']:
                if not backend.quotaholder_enabled:
                    raise CommandError('Quotaholder component is not enabled')

                if not backend.quotaholder_url:
                    raise CommandError('Quotaholder url is not set')

                if not backend.quotaholder_token:
                    raise CommandError('Quotaholder token is not set')

                while True:
                    result = backend.quotaholder.reset_holding(
                        context={},
                        clientkey='pithos',
                        reset_holding=reset_holding)

                    if not result:
                        break

                    missing_entities = [reset_holding[x].entity for x in result]
                    self.stdout.write(
                            'Unknown quotaholder users: %s\n' %
                            ', '.join(missing_entities))
                    m = 'Retrying sending quota usage for the rest...\n'
                    self.stdout.write(m)
                    missing_indexes = set(result)
                    reset_holding = [x for i, x in enumerate(reset_holding)
                                     if i not in missing_indexes]
        finally:
            backend.close()

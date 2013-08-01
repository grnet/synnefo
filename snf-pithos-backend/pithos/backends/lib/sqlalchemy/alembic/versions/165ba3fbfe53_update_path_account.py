"""update account in paths

Revision ID: 165ba3fbfe53
Revises: 3dd56e750a3
Create Date: 2012-12-04 19:08:23.933634

"""

# revision identifiers, used by Alembic.
revision = '165ba3fbfe53'
down_revision = '3dd56e750a3'

from alembic import op
from sqlalchemy.sql import table, column, and_

from astakosclient import AstakosClient
from astakosclient.errors import NoUserName, NoUUID

import functools

try:
    from progress.bar import IncrementalBar
except ImportError:
    class IncrementalBar():
        def __init__(self, label, max=100):
            print label

        def next(self):
            return

        def finish(self):
            return

import sqlalchemy as sa

catalog = {}


def _get_uuid(account, service_token, astakos_client):
    global catalog
    if account in catalog:
        return catalog[account]
    try:
        catalog[account] = astakos_client.service_get_uuid(service_token,
                                                           account)
        print '\n', account, '-->', catalog[account]
    except NoUUID:
        return None
    except:
        raise
    else:
        return catalog[account]

inverse_catalog = {}


def _get_displayname(account, service_token, astakos_client):
    global inverse_catalog
    if account in inverse_catalog:
        return inverse_catalog[account]
    try:
        inverse_catalog[account] = astakos_client.service_get_username(
            service_token, account)
        print '\n', account, '-->', inverse_catalog[account]
    except NoUserName:
        return None
    except:
        raise
    else:
        return inverse_catalog[account]

n = table(
    'nodes',
    column('node', sa.Integer),
    column('path', sa.String(2048))
)

v = table(
    'versions',
    column('node', sa.Integer),
    column('muser', sa.String(2048))
)

p = table(
    'public',
    column('public_id', sa.Integer),
    column('path', sa.String(2048))
)

x = table(
    'xfeatures',
    column('feature_id', sa.Integer),
    column('path', sa.String(2048))
)

xvals = table(
    'xfeaturevals',
    column('feature_id', sa.Integer),
    column('key', sa.Integer),
    column('value', sa.String(256))
)

g = table(
    'groups',
    column('owner', sa.String(256)),
    column('name', sa.String(256)),
    column('member', sa.String(256))
)


def migrate(callback):
    connection = op.get_bind()

    s = sa.select([n.c.node, n.c.path])
    nodes = connection.execute(s).fetchall()
    bar = IncrementalBar('Migrating node paths...', max=len(nodes))
    for node, path in nodes:
        account, sep, rest = path.partition('/')
        match = callback(account)
        if not match:
            bar.next()
            continue
        path = sep.join([match, rest])
        u = n.update().where(n.c.node == node).values({'path': path})
        connection.execute(u)
        bar.next()
    bar.finish()

    s = sa.select([v.c.muser]).distinct()
    musers = connection.execute(s).fetchall()
    bar = IncrementalBar('Migrating version modification users...',
                         max=len(musers))
    for muser, in musers:
        match = callback(muser)
        if not match:
            bar.next()
            continue
        u = v.update().where(v.c.muser == muser).values({'muser': match})
        connection.execute(u)
        bar.next()
    bar.finish()

    s = sa.select([p.c.public_id, p.c.path])
    public = connection.execute(s).fetchall()
    bar = IncrementalBar('Migrating public paths...', max=len(public))
    for id, path in public:
        account, sep, rest = path.partition('/')
        match = callback(account)
        if not match:
            bar.next()
            continue
        path = sep.join([match, rest])
        u = p.update().where(p.c.public_id == id).values({'path': path})
        connection.execute(u)
        bar.next()
    bar.finish()

    s = sa.select([x.c.feature_id, x.c.path])
    xfeatures = connection.execute(s).fetchall()
    bar = IncrementalBar('Migrating permission paths...', max=len(xfeatures))
    for id, path in xfeatures:
        account, sep, rest = path.partition('/')
        match = callback(account)
        if not match:
            bar.next()
            continue
        path = sep.join([match, rest])
        u = x.update().where(x.c.feature_id == id).values({'path': path})
        connection.execute(u)
        bar.next()
    bar.finish()

    s = sa.select([xvals.c.feature_id, xvals.c.key, xvals.c.value])
    s = s.where(xvals.c.value != '*')
    xfeaturevals = connection.execute(s).fetchall()
    bar = IncrementalBar('Migrating permission holders...',
                         max=len(xfeaturevals))
    for feature_id, key, value in xfeaturevals:
        account, sep, group = value.partition(':')
        match = callback(account)
        if not match:
            bar.next()
            continue
        new_value = sep.join([match, group])
        u = xvals.update()
        u = u.where(and_(xvals.c.feature_id == feature_id,
                         xvals.c.key == key,
                         xvals.c.value == value))
        u = u.values({'value': new_value})
        connection.execute(u)
        bar.next()
    bar.finish()

    s = sa.select([g.c.owner, g.c.name, g.c.member])
    groups = connection.execute(s).fetchall()
    bar = IncrementalBar('Migrating group owners & members...',
                         max=len(groups))
    for owner, name, member in groups:
        owner_match = callback(owner)
        member_match = callback(member)
        if owner_match or member_match:
            u = g.update()
            u = u.where(and_(
                g.c.owner == owner,
                g.c.name == name,
                g.c.member == member))
            values = {}
            if owner_match:
                values['owner'] = owner_match
            if member_match:
                values['member'] = member_match
            u = u.values(values)
            connection.execute(u)
            bar.next()
    bar.finish()


def upgrade():
    try:
        from pithos.api import settings
    except ImportError:
        return
    else:
        astakos_client = AstakosClient(settings.ASTAKOS_BASE_URL,
                                       retry=3,
                                       use_pool=True)
        get_uuid = functools.partial(_get_uuid,
                                     service_token=settings.SERVICE_TOKEN,
                                     astakos_client=astakos_client)
        migrate(get_uuid)


def downgrade():
    try:
        from pithos.api import settings
    except ImportError:
        return
    else:
        astakos_client = AstakosClient(settings.ASTAKOS_BASE_URL,
                                       retry=3,
                                       use_pool=True)
        get_displayname = functools.partial(
            _get_displayname,
            service_token=settings.SERVICE_TOKEN,
            astakos_client=astakos_client)
        migrate(get_displayname)

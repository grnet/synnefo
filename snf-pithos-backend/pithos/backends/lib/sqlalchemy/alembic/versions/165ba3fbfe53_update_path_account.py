"""update account in paths

Revision ID: 165ba3fbfe53
Revises: 3dd56e750a3
Create Date: 2012-12-04 19:08:23.933634

"""

# revision identifiers, used by Alembic.
revision = '165ba3fbfe53'
down_revision = '3dd56e750a3'

from alembic import op
from sqlalchemy.sql import table, column

from synnefo.lib.astakos import get_user_uuid, get_username as get_user_username
from pithos.api.settings import SERVICE_TOKEN, USER_INFO_URL

import sqlalchemy as sa

catalog = {}
def get_uuid(account):
    global catalog
    uuid = catalog.get(account)
    if uuid:
        return uuid
    try:
        uuid = get_user_uuid(SERVICE_TOKEN, account, USER_INFO_URL)
    except Exception, e:
        print e
        return
    else:
        if uuid:
            catalog[account] = uuid
        return uuid
    
inverse_catalog = {}
def get_username(account):
    global inverse_catalog
    username = inverse_catalog.get(account)
    if username:
        return username
    try:
        username = get_user_username(SERVICE_TOKEN, account, USER_INFO_URL)
    except Exception, e:
        print e
        return
    else:
        if username:
            catalog[account] = username
        return username

n = table(
    'nodes',
    column('node', sa.Integer),
    column('path', sa.String(2048))
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

def upgrade():
    connection = op.get_bind()
  
    s = sa.select([n.c.node, n.c.path])
    nodes = connection.execute(s).fetchall()
    for node, path in nodes:
        account, sep, rest = path.partition('/')
        uuid = get_uuid(account)
        if not uuid:
            continue
        path = sep.join([uuid, rest])
        u = n.update().where(n.c.node == node).values({'path':path})
        connection.execute(u)
    
    s = sa.select([p.c.public_id, p.c.path])
    public = connection.execute(s).fetchall()
    for id, path in public:
        account, sep, rest = path.partition('/')
        uuid = get_uuid(account)
        if not uuid:
            continue
        path = sep.join([uuid, rest])
        u = p.update().where(p.c.public_id == id).values({'path':path})
        connection.execute(u)
    
    s = sa.select([x.c.feature_id, x.c.path])
    xfeatures = connection.execute(s).fetchall()
    for id, path in xfeatures:
        account, sep, rest = path.partition('/')
        uuid = get_uuid(account)
        if not uuid:
            continue
        path = sep.join([uuid, rest])
        u = x.update().where(x.c.feature_id == id).values({'path':path})
        connection.execute(u)


def downgrade():
    connection = op.get_bind()
  
    s = sa.select([n.c.node, n.c.path])
    nodes = connection.execute(s).fetchall()
    for node, path in nodes:
        account, sep, rest = path.partition('/')
        username = get_username(account)
        if not username:
            continue
        path = sep.join([username, rest])
        u = n.update().where(n.c.node == node).values({'path':path})
        connection.execute(u)
    
    s = sa.select([p.c.public_id, p.c.path])
    public = connection.execute(s).fetchall()
    for id, path in public:
        account, sep, rest = path.partition('/')
        username = get_username(account)
        if not username:
            continue
        path = sep.join([username, rest])
        u = p.update().where(p.c.public_id == id).values({'path':path})
        connection.execute(u)
    
    s = sa.select([x.c.feature_id, x.c.path])
    xfeatures = connection.execute(s).fetchall()
    for id, path in xfeatures:
        account, sep, rest = path.partition('/')
        username = get_username(account)
        if not username:
            continue
        path = sep.join([username, rest])
        u = x.update().where(x.c.feature_id == id).values({'path':path})
        connection.execute(u)

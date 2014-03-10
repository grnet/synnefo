"""Split plankton properties

Revision ID: 54dbdde2d187
Revises: 3b62b3f1bf6c
Create Date: 2014-01-21 11:44:34.783895

"""

# revision identifiers, used by Alembic.
revision = '54dbdde2d187'
down_revision = '3b62b3f1bf6c'

from alembic import op
import sqlalchemy as sa

import json

from collections import defaultdict


def upgrade():
    c = op.get_bind()
    a = sa.sql.table(
        'attributes',
        sa.sql.column('serial', sa.Integer),
        sa.sql.column('domain', sa.String),
        sa.sql.column('key', sa.String),
        sa.sql.column('value', sa.String),
        sa.sql.column('node', sa.Integer),
        sa.sql.column('is_latest', sa.Boolean))

    s = sa.select([a.c.serial,
                   a.c.domain,
                   a.c.key,
                   a.c.value,
                   a.c.node,
                   a.c.is_latest])
    cond = sa.sql.and_(a.c.domain == 'plankton',
                       a.c.key == 'plankton:properties')
    s = s.where(cond)
    entries = c.execute(s).fetchall()
    if not entries:
        return

    values = []
    for e in entries:
        d = dict(e.items())
        properties = json.loads(e['value'])
        for k, v in properties.items():
            copy = d.copy()
            copy.update({'key': 'plankton:property:%s' % k,
                         'value': v})
            values.append(copy)

    op.bulk_insert(a, values)

    d = a.delete().where(cond)
    op.execute(d)


def downgrade():
    c = op.get_bind()
    a = sa.sql.table(
        'attributes',
        sa.sql.column('serial', sa.Integer),
        sa.sql.column('domain', sa.String),
        sa.sql.column('key', sa.String),
        sa.sql.column('value', sa.String),
        sa.sql.column('node', sa.Integer),
        sa.sql.column('is_latest', sa.Boolean))

    s = sa.select([a.c.serial,
                   a.c.domain,
                   a.c.key,
                   a.c.value,
                   a.c.node,
                   a.c.is_latest])
    cond = sa.sql.and_(a.c.domain == 'plankton',
                       a.c.key.like('plankton:property:%'))
    s = s.where(cond)
    entries = c.execute(s).fetchall()
    if not entries:
        return

    props = defaultdict(dict)
    for e in entries:
        k = e.key.replace('plankton:property:', '', 1)
        props[(e.serial, e.domain, e.node, e.is_latest)][k] = e.value

    values = []
    for k in props:
        serial, domain, node, is_latest = k
        values.append({'serial': serial,
                       'domain': domain,
                       'node': node,
                       'is_latest': is_latest,
                       'key': 'plankton:properties',
                       'value': json.dumps(props[k])})

    op.bulk_insert(a, values)

    d = a.delete().where(cond)
    op.execute(d)

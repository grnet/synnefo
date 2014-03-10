"""Set container quota source

Revision ID: 4451e165da19
Revises: 301fba21d9b8
Create Date: 2013-09-27 13:36:27.477141

"""

# revision identifiers, used by Alembic.
revision = '4451e165da19'
down_revision = '301fba21d9b8'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select

ROOTNODE = 0


def upgrade():
    connection = op.get_bind()

    nodes = table('nodes',
                  column('path', sa.String(2048)),
                  column('node', sa.Integer),
                  column('parent', sa.Integer))
    n1 = nodes.alias('n1')
    n2 = nodes.alias('n2')
    policy = table('policy',
                   column('node', sa.Integer),
                   column('key', sa.String(128)),
                   column('value', sa.String(256)))

    s = select([n2.c.node, n1.c.path])
    s = s.where(n2.c.parent == n1.c.node)
    s = s.where(n1.c.parent == ROOTNODE)
    s = s.where(n1.c.node != ROOTNODE)
    r = connection.execute(s)
    rows = r.fetchall()
    op.bulk_insert(policy, [{'node': node,
                             'key': 'project',
                             'value': path} for node, path in rows])


def downgrade():
    pass

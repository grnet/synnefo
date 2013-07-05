"""add attributes node column

Revision ID: 3b62b3f1bf6c
Revises: 4c8ccdc58192
Create Date: 2013-07-04 13:11:01.842706

"""

# revision identifiers, used by Alembic.
revision = '3b62b3f1bf6c'
down_revision = '4c8ccdc58192'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, and_


def upgrade():
    op.add_column('attributes',
                  sa.Column('node', sa.Integer, default=0))
    op.add_column('attributes',
                  sa.Column('is_latest', sa.Boolean, default=True))

    n = table('nodes',
              column('node', sa.Integer),
              column('latest_version', sa.Integer))
    v = table('versions',
              column('node', sa.Integer),
              column('serial', sa.Integer))
    a = table('attributes',
              column('serial', sa.Integer),
              column('node', sa.Integer),
              column('is_latest', sa.Boolean))

    s = sa.select([v.c.node]).where(v.c.serial == a.c.serial)
    u = a.update().values({'node': s})
    op.execute(u)

    s = sa.select([v.c.serial == n.c.latest_version],
                  and_(a.c.node == n.c.node, a.c.serial == v.c.serial))
    u = a.update().values({'is_latest': s})
    op.execute(u)

    op.alter_column('attributes', 'node', nullable=False)
    op.alter_column('attributes', 'is_latest', nullable=False)

    op.create_index('idx_attributes_serial_node', 'attributes',
                    ['serial', 'node'])


def downgrade():
    op.drop_index('idx_attributes_serial_node')

    op.drop_column('attributes', 'is_latest')
    op.drop_column('attributes', 'node')

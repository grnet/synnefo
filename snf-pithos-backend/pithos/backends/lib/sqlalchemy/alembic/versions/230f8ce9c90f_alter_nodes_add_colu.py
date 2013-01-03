"""alter nodes add column latest version

Revision ID: 230f8ce9c90f
Revises: 8320b1c62d9
Create Date: 2012-07-17 20:32:54.466145

"""

# revision identifiers, used by Alembic.
revision = '230f8ce9c90f'
down_revision = '8320b1c62d9'

from alembic import op, context
from sqlalchemy.sql import table, column
from alembic import op

import sqlalchemy as sa


def upgrade():
    op.add_column('nodes', sa.Column('latest_version', sa.INTEGER))

    n = table(
        'nodes',
        column('node', sa.Integer),
        column('latest_version', sa.Integer)
    )
    v = table(
        'versions',
        column('node', sa.Integer),
        column('mtime', sa.Integer),
        column('serial', sa.Integer),
    )

    s = sa.select(
        [v.c.serial]).where(n.c.node == v.c.node).order_by(v.c.mtime).limit(1)
    op.execute(
        n.update().
        values({'latest_version': s})
    )


def downgrade():
    op.drop_column('nodes', 'latest_version')

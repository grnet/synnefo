"""Fix latest_version

Revision ID: 3dd56e750a3
Revises: 230f8ce9c90f
Create Date: 2012-07-19 14:36:24.242310

"""

# revision identifiers, used by Alembic.
revision = '3dd56e750a3'
down_revision = '230f8ce9c90f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.sql.expression import desc

def upgrade():
    n = table('nodes', 
        column('node', sa.Integer),
        column('latest_version', sa.Integer)
    )
    v = table('versions', 
        column('node', sa.Integer),
        column('mtime', sa.Integer),
        column('serial', sa.Integer),
    )
    
    s = sa.select([v.c.serial]).where(n.c.node == v.c.node).order_by(desc(v.c.mtime)).limit(1)
    op.execute(
        n.update().\
            values({'latest_version':s})
            )


def downgrade():
    pass

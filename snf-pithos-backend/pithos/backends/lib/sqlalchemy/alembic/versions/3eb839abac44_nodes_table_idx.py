"""nodes table idx

Revision ID: 3eb839abac44
Revises: 2be04d9180dd
Create Date: 2014-08-02 11:54:08.902956

"""

# revision identifiers, used by Alembic.
revision = '3eb839abac44'
down_revision = '2be04d9180dd'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


def upgrade():
    op.create_index('idx_nodes_parent0','nodes', ['parent'],
                    postgresql_where=text('nodes.parent=0'))
    op.create_index('idx_nodes_parent0_path','nodes', ['parent', 'path'],
                    postgresql_where=text('nodes.parent=0'))


def downgrade():
    op.drop_index('idx_nodes_parent0', tablename='nodes')
    op.drop_index('idx_nodes_parent0_path', tablename='nodes')

"""create index nodes.parent

Revision ID: 8320b1c62d9
Revises: None
Create Date: 2012-07-17 20:31:18.790919

"""

# revision identifiers, used by Alembic.
revision = '8320b1c62d9'
down_revision = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_index('idx_nodes_parent', 'nodes', ['parent'])

def downgrade():
    op.drop_index('idx_nodes_parent', tablename='nodes')

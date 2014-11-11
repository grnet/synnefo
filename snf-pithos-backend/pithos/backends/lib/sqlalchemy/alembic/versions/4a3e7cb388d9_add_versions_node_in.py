"""Add versions node index

Revision ID: 4a3e7cb388d9
Revises: 2efddde15abf
Create Date: 2014-07-22 13:21:02.392998

"""

# revision identifiers, used by Alembic.
revision = '4a3e7cb388d9'
down_revision = '2efddde15abf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index('idx_versions_node', 'versions', ['node'])


def downgrade():
    op.drop_index('idx_versions_node', tablename='versions')

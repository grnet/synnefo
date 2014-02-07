"""add nodes latest_version index

Revision ID: 301fba21d9b8
Revises: 54dbdde2d187
Create Date: 2014-02-07 13:39:10.221706

"""

# revision identifiers, used by Alembic.
revision = '301fba21d9b8'
down_revision = '54dbdde2d187'

from alembic import op


def upgrade():
    op.create_index('idx_latest_version', 'nodes', ['latest_version'])


def downgrade():
    op.drop_index('idx_latest_version', 'nodes')

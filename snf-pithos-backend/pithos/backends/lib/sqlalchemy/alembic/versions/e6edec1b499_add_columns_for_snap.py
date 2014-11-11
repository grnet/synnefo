"""Add columns for snapshots

Revision ID: e6edec1b499
Revises: 4451e165da19
Create Date: 2014-01-27 15:33:21.058484

"""

# revision identifiers, used by Alembic.
revision = 'e6edec1b499'
down_revision = '4451e165da19'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('versions',
                  sa.Column('available', sa.Boolean, nullable=False,
                            server_default='true'))
    op.add_column('versions',
                  sa.Column('map_check_timestamp',
                            sa.DECIMAL(precision=16, scale=6)))


def downgrade():
    op.drop_column('versions', 'available')
    op.drop_column('versions', 'map_check_timestamp')

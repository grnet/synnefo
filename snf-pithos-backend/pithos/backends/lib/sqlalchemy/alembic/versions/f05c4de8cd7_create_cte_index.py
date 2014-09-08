"""create_cte_index

Revision ID: f05c4de8cd7
Revises: 4a3e7cb388d9
Create Date: 2014-07-29 11:27:55.421353

"""

# revision identifiers, used by Alembic.
revision = 'f05c4de8cd7'
down_revision = '4a3e7cb388d9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


def upgrade():
    op.create_index('idx_versions_serial_cluster_n2', 'versions',
                    ['serial', 'cluster'],
                    postgresql_where=text("versions.cluster != 2"))


def downgrade():
    op.drop_index('idx_versions_serial_cluster_n2', tablename='versions')
    pass

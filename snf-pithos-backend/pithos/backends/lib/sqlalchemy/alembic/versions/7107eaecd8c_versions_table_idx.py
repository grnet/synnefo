"""versions table idx

Revision ID: 7107eaecd8c
Revises: 3eb839abac44
Create Date: 2014-08-02 11:44:37.072969

"""

# revision identifiers, used by Alembic.
revision = '7107eaecd8c'
down_revision = '3eb839abac44'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


def upgrade():
    op.create_index('idx_versions_node_cluster0', 'versions',
                    ['node', 'cluster'],
                    postgresql_where=text("versions.cluster=0"))
    op.create_index('idx_versions_node_cluster1', 'versions',
                    ['node', 'cluster'],
                    postgresql_where=text("versions.cluster=1"))
    op.create_index('idx_versions_node_cluster2', 'versions',
                    ['node', 'cluster'],
                    postgresql_where=text("versions.cluster=2"))
    op.create_index('idx_versions_serial_cluster0', 'versions',
                    ['serial', 'cluster'],
                    postgresql_where=text("versions.cluster=0"))
    op.create_index('idx_versions_serial_cluster1', 'versions',
                    ['serial', 'cluster'],
                    postgresql_where=text("versions.cluster=1"))
    op.create_index('idx_versions_serial_cluster2', 'versions',
                    ['serial', 'cluster'],
                    postgresql_where=text("versions.cluster=2"))

def downgrade():
    op.drop_index('idx_versions_node_cluster0', tablename='versions')
    op.drop_index('idx_versions_node_cluster1', tablename='versions')
    op.drop_index('idx_versions_node_cluster2', tablename='versions')
    op.drop_index('idx_versions_serial_cluster0', tablename='versions')
    op.drop_index('idx_versions_serial_cluster1', tablename='versions')
    op.drop_index('idx_versions_serial_cluster2', tablename='versions')

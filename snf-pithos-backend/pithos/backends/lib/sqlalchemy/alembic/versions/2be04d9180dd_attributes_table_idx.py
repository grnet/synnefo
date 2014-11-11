"""attributes table idxs

Revision ID: 2be04d9180dd
Revises: 1d40ec1ccc4f
Create Date: 2014-08-02 10:48:15.925018

"""

# revision identifiers, used by Alembic.
revision = '2be04d9180dd'
down_revision = '1d40ec1ccc4f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


def upgrade():
    op.create_index('idx_attributes_node', 'attributes',['node'])
    op.create_index('idx_attributes_islatest_domain_plankton', 'attributes',
                    ['is_latest', 'domain'],
                    postgresql_where=text("attributes.is_latest=true and "
                                          "attributes.domain='plankton'"))
    op.create_index('idx_attributes_key_domain_plankton', 'attributes',
                    ['key', 'domain'],
                    postgresql_where=text("attributes.domain='plankton'"))
    op.create_index('idx_attributes_key_domain_pithos', 'attributes',
                    ['key', 'domain'],
                    postgresql_where=text("attributes.domain='pithos'"))
    op.create_index('idx_attributes_serial_domain_pithos', 'attributes',
                    ['serial', 'domain'],
                    postgresql_where=text("attributes.domain='pithos'"))
    op.create_index('idx_attributes_serial_domain_plankton', 'attributes',
                    ['serial', 'domain'],
                    postgresql_where=text("attributes.domain='plankton'"))

def downgrade():
    op.drop_index('idx_attributes_node', tablename='attributes')
    op.drop_index('idx_attributes_islatest_domain_plankton',
                  tablename='attributes')
    op.drop_index('idx_attributes_key_domain_plankton',
                  tablename='attributes')
    op.drop_index('idx_attributes_key_domain_pithos',
                  tablename='attributes')
    op.drop_index('idx_attributes_serial_domain_pithos',
                  tablename='attributes')
    op.drop_index('idx_attributes_serial_domain_plankton',
                  tablename='attributes')

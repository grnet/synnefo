"""add attributes domain index

Revision ID: 4c8ccdc58192
Revises: 27381099d477
Create Date: 2013-04-01 15:37:05.750288

"""

# revision identifiers, used by Alembic.
revision = '4c8ccdc58192'
down_revision = '27381099d477'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index('idx_attributes_domain', 'attributes', ['domain'])


def downgrade():
    op.drop_index('idx_attributes_domain', tablename='attributes')

"""Differentiate hashmap from mapfile

Revision ID: 2efddde15abf
Revises: e6edec1b499
Create Date: 2014-06-11 10:46:04.116321

"""

# revision identifiers, used by Alembic.
revision = '2efddde15abf'
down_revision = 'e6edec1b499'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute(sa.schema.CreateSequence(sa.schema.Sequence("mapfile_seq")))

    op.add_column('versions', sa.Column('mapfile', sa.String(256)))
    op.add_column('versions', sa.Column('is_snapshot', sa.Boolean,
                                        nullable=False, default=False,
                                        server_default='False'))

    v = sa.sql.table(
        'versions',
        sa.sql.column('hash', sa.String),
        sa.sql.column('mapfile', sa.String),
        sa.sql.column('is_snapshot', sa.Boolean))

    u = v.update().values({'mapfile': v.c.hash,
                           'is_snapshot': sa.case([(v.c.hash.like('archip:%'),
                                                  True)], else_=False)})
    op.execute(u)


def downgrade():
    op.drop_column('versions', 'is_snapshot')
    op.drop_column('versions', 'mapfile')

    op.execute(sa.schema.DropSequence(sa.schema.Sequence("mapfile_seq")))

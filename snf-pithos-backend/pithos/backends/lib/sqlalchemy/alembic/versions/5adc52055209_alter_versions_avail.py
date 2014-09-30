"""Alter versions available possible states

Revision ID: 5adc52055209
Revises: 7107eaecd8c
Create Date: 2014-09-12 18:42:27.307379

"""

# revision identifiers, used by Alembic.
revision = '5adc52055209'
down_revision = '7107eaecd8c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('versions', sa.Column('temp', sa.INTEGER))

    v = sa.sql.table(
        'versions',
        sa.sql.column('available', sa.Boolean),
        sa.sql.column('temp', sa.Integer))

    u = v.update().values({'temp': sa.case([(v.c.available ==
                                             sa.sql.expression.true(), 1)],
                                           else_=0)})
    op.execute(u)

    op.drop_column('versions', 'available')
    op.add_column('versions', sa.Column('available', sa.INTEGER))
    u = v.update().values({'available': v.c.temp})
    op.execute(u)

    op.drop_column('versions', 'temp')


def downgrade():
    op.add_column('versions', sa.Column('temp', sa.Boolean))

    v = sa.sql.table(
        'versions',
        sa.sql.column('available', sa.Boolean),
        sa.sql.column('temp', sa.Integer))

    u = v.update().values({'temp': sa.case([(v.c.available == 1,
                                             sa.sql.expression.true())],
                                           else_=False)})
    op.execute(u)

    op.drop_column('versions', 'available')
    op.add_column('versions', sa.Column('available', sa.Boolean))
    u = v.update().values({'available': v.c.temp})
    op.execute(u)

    op.drop_column('versions', 'temp')

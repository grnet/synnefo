"""Check/fix version size

Revision ID: 1d40ec1ccc4f
Revises: f05c4de8cd7
Create Date: 2014-08-04 12:22:59.710166

"""

# revision identifiers, used by Alembic.
revision = '1d40ec1ccc4f'
down_revision = 'f05c4de8cd7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    v = sa.sql.table('versions',
                     sa.sql.column('serial', sa.Integer),
                     sa.sql.column('size', sa.Integer))

    s = sa.select([v.c.serial], v.c.size < 0)
    c = op.get_bind()
    rp = c.execute(s)
    serials = list(r.serial for r in rp.fetchall())

    if serials:
        print('Negative object sizes are found for the following serials: %s\n'
              'Their size will be set to 0.' %
              ','.join([unicode(srl) for srl in serials]))
        u = v.update().where(v.c.serial.in_(serials)).values({'size': 0})
        op.execute(u)


def downgrade():
    pass

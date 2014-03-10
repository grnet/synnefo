"""alter public add column url

Revision ID: 27381099d477
Revises: 2a309a9a3438
Create Date: 2013-03-20 16:14:20.058077

"""

# revision identifiers, used by Alembic.
revision = '27381099d477'
down_revision = '2a309a9a3438'

from alembic import op
import sqlalchemy as sa

from pithos.backends.modular import ULTIMATE_ANSWER


def upgrade():
    op.add_column('public', sa.Column('url', sa.String(2048)))
    op.create_unique_constraint('idx_public_url', 'public', ['url'])

    # migrate old rows
    p = sa.sql.table(
        'public',
        sa.sql.column('public_id', sa.Integer),
        sa.sql.column('url', sa.String),
    )

    try:
        from pithos.api.short_url import encode_url
    except ImportError:
        return
    else:
        get_url = lambda x: encode_url(x + ULTIMATE_ANSWER)
        conn = op.get_bind()
        s = sa.select([p.c.public_id])
        rows = conn.execute(s).fetchall()
        for r in rows:
            s = p.update().values(url=get_url(r[0])).where(
                p.c.public_id == r[0])
            op.execute(s)


def downgrade():
    op.drop_constraint('idx_public_url', 'public')
    op.drop_column('public', 'url')

"""fix statistics negative population

Revision ID: 2a309a9a3438
Revises: 165ba3fbfe53
Create Date: 2013-01-02 09:12:30.222261

"""

# revision identifiers, used by Alembic.
revision = '2a309a9a3438'
down_revision = '165ba3fbfe53'

from alembic import op
import sqlalchemy as sa


def upgrade():
    st = sa.sql.table(
        'statistics',
        sa.sql.column('node', sa.Integer),
        sa.sql.column('population', sa.Integer)
    )

    u = st.update().where(st.c.population < 0).values({'population': 0})
    op.execute(u)

def downgrade():
    pass

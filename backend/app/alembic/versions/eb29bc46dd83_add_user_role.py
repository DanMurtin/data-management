"""empty message

Revision ID: eb29bc46dd83
Revises: 1a31ce608336
Create Date: 2024-12-11 13:15:53.698400

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'eb29bc46dd83'
down_revision = '1a31ce608336'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('role', sa.String, nullable=True))
    op.execute("""
        UPDATE "user"
        SET role = CASE
            WHEN is_superuser = TRUE THEN 'admin'
            ELSE 'client'
        END
    """)
    op.alter_column('user', 'role', nullable=False)
    op.drop_column('user', 'is_superuser')


def downgrade():
    op.drop_column('user', 'role')

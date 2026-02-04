"""Add training_logs column to training_sessions

Revision ID: a1b2c3d4e5f7
Revises: 66c704a2b53f
Create Date: 2025-12-10 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = '66c704a2b53f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (SQLite compatible)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('training_sessions', 'training_logs'):
        op.add_column(
            'training_sessions',
            sa.Column('training_logs', sa.Text(), nullable=True, comment='Training logs captured from the worker')
        )


def downgrade() -> None:
    if column_exists('training_sessions', 'training_logs'):
        op.drop_column('training_sessions', 'training_logs')

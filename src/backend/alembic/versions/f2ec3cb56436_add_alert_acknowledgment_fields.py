"""add alert acknowledgment fields

Revision ID: f2ec3cb56436
Revises: ec1c3fa21321
Create Date: 2026-01-04 08:54:29.814557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2ec3cb56436'
down_revision: Union[str, None] = 'ec1c3fa21321'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (SQLite compatible)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Idempotent migration - only add columns if they don't exist
    if not column_exists('alert_history', 'acknowledged'):
        op.add_column('alert_history', sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default=sa.false()))

    if not column_exists('alert_history', 'acknowledged_at'):
        op.add_column('alert_history', sa.Column('acknowledged_at', sa.DateTime(), nullable=True))

    if not column_exists('alert_history', 'acknowledged_by'):
        op.add_column('alert_history', sa.Column('acknowledged_by', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Only drop columns if they exist
    if column_exists('alert_history', 'acknowledged_by'):
        op.drop_column('alert_history', 'acknowledged_by')

    if column_exists('alert_history', 'acknowledged_at'):
        op.drop_column('alert_history', 'acknowledged_at')

    if column_exists('alert_history', 'acknowledged'):
        op.drop_column('alert_history', 'acknowledged')

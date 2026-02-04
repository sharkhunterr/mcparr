"""Add external_url to service_configs

Revision ID: ec1c3fa21321
Revises: a1b2c3d4e5f7
Create Date: 2025-07-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec1c3fa21321'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (SQLite compatible)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Idempotent migration - only add column if it doesn't exist
    if not column_exists('service_configs', 'external_url'):
        op.add_column('service_configs', sa.Column('external_url', sa.String(255), nullable=True))


def downgrade() -> None:
    # Only drop column if it exists
    if column_exists('service_configs', 'external_url'):
        op.drop_column('service_configs', 'external_url')

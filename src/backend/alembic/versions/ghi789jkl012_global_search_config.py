"""Add global_search_configs table for multi-service search configuration

This migration adds the global_search_configs table that stores which services
are enabled for the system_global_search MCP tool.

Revision ID: ghi789jkl012
Revises: def456ghi789
Create Date: 2026-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ghi789jkl012'
down_revision: Union[str, None] = 'def456ghi789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create global_search_configs table
    op.create_table(
        'global_search_configs',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('service_config_id', sa.String(36), sa.ForeignKey('service_configs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('priority', sa.Integer(), default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create index on service_config_id
    op.create_index(
        'ix_global_search_configs_service_config_id',
        'global_search_configs',
        ['service_config_id']
    )

    # Create index on enabled for faster filtering
    op.create_index(
        'ix_global_search_configs_enabled',
        'global_search_configs',
        ['enabled']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_global_search_configs_enabled', 'global_search_configs')
    op.drop_index('ix_global_search_configs_service_config_id', 'global_search_configs')

    # Drop table
    op.drop_table('global_search_configs')

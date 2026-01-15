"""update_tool_chains_architecture

Revision ID: 7007e2ea11ab
Revises: f2ec3cb56436
Create Date: 2026-01-12 13:18:15.319620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '7007e2ea11ab'
down_revision: Union[str, None] = 'f2ec3cb56436'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support adding NOT NULL columns without defaults
    # So we use batch mode for SQLite compatibility

    # Get connection to check if table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. First, create the new tool_chain_step_targets table (if not exists)
    if 'tool_chain_step_targets' not in existing_tables:
        op.create_table('tool_chain_step_targets',
            sa.Column('step_id', sa.String(length=36), nullable=False),
            sa.Column('target_service', sa.String(length=50), nullable=False),
            sa.Column('target_tool', sa.String(length=100), nullable=False),
            sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('execution_mode', sa.String(length=20), nullable=False, server_default='sequential'),
            sa.Column('argument_mappings', sa.JSON(), nullable=True),
            sa.Column('target_ai_comment', sa.Text(), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['step_id'], ['tool_chain_steps.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_tool_chain_step_targets_step_id'), 'tool_chain_step_targets', ['step_id'], unique=False)

    # 2. Update tool_chains table - add color, remove old columns
    with op.batch_alter_table('tool_chains', schema=None) as batch_op:
        batch_op.add_column(sa.Column('color', sa.String(length=20), nullable=False, server_default='#8b5cf6'))
        # Drop old columns that were moved to steps
        batch_op.drop_index('ix_tool_chains_source_service')
        batch_op.drop_index('ix_tool_chains_source_tool')
        batch_op.drop_column('condition_value')
        batch_op.drop_column('ai_comment')
        batch_op.drop_column('source_tool')
        batch_op.drop_column('condition_field')
        batch_op.drop_column('source_service')
        batch_op.drop_column('condition_operator')

    # 3. Update tool_chain_steps table - add source_tool/condition fields, remove target fields
    with op.batch_alter_table('tool_chain_steps', schema=None) as batch_op:
        # Add new columns with defaults for existing rows
        batch_op.add_column(sa.Column('source_service', sa.String(length=50), nullable=False, server_default='system'))
        batch_op.add_column(sa.Column('source_tool', sa.String(length=100), nullable=False, server_default='unknown'))
        batch_op.add_column(sa.Column('condition_operator', sa.String(length=20), nullable=False, server_default='success'))
        batch_op.add_column(sa.Column('condition_field', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('condition_value', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ai_comment', sa.Text(), nullable=True))
        batch_op.create_index('ix_tool_chain_steps_source_service', ['source_service'], unique=False)
        batch_op.create_index('ix_tool_chain_steps_source_tool', ['source_tool'], unique=False)
        # Drop old columns that were moved to targets
        batch_op.drop_column('target_service')
        batch_op.drop_column('step_condition_field')
        batch_op.drop_column('step_condition_value')
        batch_op.drop_column('step_condition_operator')
        batch_op.drop_column('execution_mode')
        batch_op.drop_column('step_ai_comment')
        batch_op.drop_column('target_tool')
        batch_op.drop_column('argument_mappings')


def downgrade() -> None:
    # Reverse migration - restore old structure

    # 1. Update tool_chain_steps - restore target columns, remove source columns
    with op.batch_alter_table('tool_chain_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('argument_mappings', sqlite.JSON(), nullable=True))
        batch_op.add_column(sa.Column('target_tool', sa.VARCHAR(length=100), nullable=False, server_default='unknown'))
        batch_op.add_column(sa.Column('step_ai_comment', sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column('execution_mode', sa.VARCHAR(length=20), nullable=False, server_default='sequential'))
        batch_op.add_column(sa.Column('step_condition_operator', sa.VARCHAR(length=20), nullable=True))
        batch_op.add_column(sa.Column('step_condition_value', sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column('step_condition_field', sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(sa.Column('target_service', sa.VARCHAR(length=50), nullable=False, server_default='system'))
        batch_op.drop_index('ix_tool_chain_steps_source_tool')
        batch_op.drop_index('ix_tool_chain_steps_source_service')
        batch_op.drop_column('ai_comment')
        batch_op.drop_column('condition_value')
        batch_op.drop_column('condition_field')
        batch_op.drop_column('condition_operator')
        batch_op.drop_column('source_tool')
        batch_op.drop_column('source_service')

    # 2. Update tool_chains - restore source/condition columns, remove color
    with op.batch_alter_table('tool_chains', schema=None) as batch_op:
        batch_op.add_column(sa.Column('condition_operator', sa.VARCHAR(length=20), nullable=False, server_default='success'))
        batch_op.add_column(sa.Column('source_service', sa.VARCHAR(length=50), nullable=False, server_default='system'))
        batch_op.add_column(sa.Column('condition_field', sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(sa.Column('source_tool', sa.VARCHAR(length=100), nullable=False, server_default='unknown'))
        batch_op.add_column(sa.Column('ai_comment', sa.TEXT(), nullable=True))
        batch_op.add_column(sa.Column('condition_value', sa.TEXT(), nullable=True))
        batch_op.create_index('ix_tool_chains_source_tool', ['source_tool'], unique=False)
        batch_op.create_index('ix_tool_chains_source_service', ['source_service'], unique=False)
        batch_op.drop_column('color')

    # 3. Drop the new targets table
    op.drop_index(op.f('ix_tool_chain_step_targets_step_id'), table_name='tool_chain_step_targets')
    op.drop_table('tool_chain_step_targets')

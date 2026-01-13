"""if_then_else_tool_chains

Revision ID: abc123def456
Revises: 7007e2ea11ab
Create Date: 2026-01-13 09:00:00.000000

Complete restructure of tool chains to support IF/THEN/ELSE logic with:
- Compound conditions (AND/OR groups)
- THEN and ELSE branches with actions
- Action types: tool_call or message
- Step position types: middle or end
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, None] = '7007e2ea11ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check existing tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Drop old targets table
    if 'tool_chain_step_targets' in existing_tables:
        op.drop_index(op.f('ix_tool_chain_step_targets_step_id'), table_name='tool_chain_step_targets')
        op.drop_table('tool_chain_step_targets')

    # 2. Drop old steps table
    if 'tool_chain_steps' in existing_tables:
        op.drop_index('ix_tool_chain_steps_source_service', table_name='tool_chain_steps')
        op.drop_index('ix_tool_chain_steps_source_tool', table_name='tool_chain_steps')
        op.drop_table('tool_chain_steps')

    # 3. Drop old chains table
    if 'tool_chains' in existing_tables:
        op.drop_table('tool_chains')

    # 4. Create new tool_chains table
    op.create_table('tool_chains',
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=False, server_default='#8b5cf6'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_chains_name'), 'tool_chains', ['name'], unique=False)

    # 5. Create new tool_chain_steps table
    op.create_table('tool_chain_steps',
        sa.Column('chain_id', sa.String(length=36), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('position_type', sa.String(length=20), nullable=False, server_default='middle'),
        sa.Column('source_service', sa.String(length=50), nullable=False),
        sa.Column('source_tool', sa.String(length=100), nullable=False),
        sa.Column('ai_comment', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['chain_id'], ['tool_chains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_chain_steps_chain_id'), 'tool_chain_steps', ['chain_id'], unique=False)
    op.create_index(op.f('ix_tool_chain_steps_source_service'), 'tool_chain_steps', ['source_service'], unique=False)
    op.create_index(op.f('ix_tool_chain_steps_source_tool'), 'tool_chain_steps', ['source_tool'], unique=False)

    # 6. Create tool_chain_condition_groups table
    op.create_table('tool_chain_condition_groups',
        sa.Column('step_id', sa.String(length=36), nullable=False),
        sa.Column('parent_group_id', sa.String(length=36), nullable=True),
        sa.Column('operator', sa.String(length=10), nullable=False, server_default='and'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['parent_group_id'], ['tool_chain_condition_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['tool_chain_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_chain_condition_groups_step_id'), 'tool_chain_condition_groups', ['step_id'], unique=False)
    op.create_index(op.f('ix_tool_chain_condition_groups_parent_group_id'), 'tool_chain_condition_groups', ['parent_group_id'], unique=False)

    # 7. Create tool_chain_conditions table
    op.create_table('tool_chain_conditions',
        sa.Column('group_id', sa.String(length=36), nullable=False),
        sa.Column('operator', sa.String(length=20), nullable=False),
        sa.Column('field', sa.String(length=100), nullable=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['group_id'], ['tool_chain_condition_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_chain_conditions_group_id'), 'tool_chain_conditions', ['group_id'], unique=False)

    # 8. Create tool_chain_actions table (for both THEN and ELSE branches)
    op.create_table('tool_chain_actions',
        sa.Column('step_id', sa.String(length=36), nullable=False),
        sa.Column('branch', sa.String(length=10), nullable=False),  # 'then' or 'else'
        sa.Column('action_type', sa.String(length=20), nullable=False, server_default='tool_call'),
        sa.Column('target_service', sa.String(length=50), nullable=True),
        sa.Column('target_tool', sa.String(length=100), nullable=True),
        sa.Column('argument_mappings', sa.JSON(), nullable=True),
        sa.Column('message_template', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_mode', sa.String(length=20), nullable=False, server_default='sequential'),
        sa.Column('ai_comment', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['step_id'], ['tool_chain_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_chain_actions_step_id'), 'tool_chain_actions', ['step_id'], unique=False)
    op.create_index(op.f('ix_tool_chain_actions_branch'), 'tool_chain_actions', ['branch'], unique=False)


def downgrade() -> None:
    # Drop all new tables
    op.drop_index(op.f('ix_tool_chain_actions_branch'), table_name='tool_chain_actions')
    op.drop_index(op.f('ix_tool_chain_actions_step_id'), table_name='tool_chain_actions')
    op.drop_table('tool_chain_actions')

    op.drop_index(op.f('ix_tool_chain_conditions_group_id'), table_name='tool_chain_conditions')
    op.drop_table('tool_chain_conditions')

    op.drop_index(op.f('ix_tool_chain_condition_groups_parent_group_id'), table_name='tool_chain_condition_groups')
    op.drop_index(op.f('ix_tool_chain_condition_groups_step_id'), table_name='tool_chain_condition_groups')
    op.drop_table('tool_chain_condition_groups')

    op.drop_index(op.f('ix_tool_chain_steps_source_tool'), table_name='tool_chain_steps')
    op.drop_index(op.f('ix_tool_chain_steps_source_service'), table_name='tool_chain_steps')
    op.drop_index(op.f('ix_tool_chain_steps_chain_id'), table_name='tool_chain_steps')
    op.drop_table('tool_chain_steps')

    op.drop_index(op.f('ix_tool_chains_name'), table_name='tool_chains')
    op.drop_table('tool_chains')

    # Note: The previous structure would need to be recreated manually if downgrade is needed
    # This is a breaking change - no automatic restoration of old data

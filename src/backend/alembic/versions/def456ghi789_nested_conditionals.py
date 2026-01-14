"""Add nested IF/THEN/ELSE conditionals support

This migration adds support for nested conditional actions within tool chains:
- Actions can now have a parent_action_id for nesting (IF/THEN/ELSE within IF/THEN/ELSE)
- Condition groups can be attached to actions (not just steps) via action_id
- step_id is now nullable on both condition_groups and actions for nested elements

Revision ID: def456ghi789
Revises: abc123def456
Create Date: 2026-01-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'def456ghi789'
down_revision: Union[str, None] = 'abc123def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add action_id to condition_groups for conditions on conditional actions
    op.add_column(
        'tool_chain_condition_groups',
        sa.Column('action_id', sa.String(36), nullable=True)
    )
    op.create_index(
        'ix_tool_chain_condition_groups_action_id',
        'tool_chain_condition_groups',
        ['action_id']
    )

    # 2. Make step_id nullable in condition_groups (for action-level conditions)
    with op.batch_alter_table('tool_chain_condition_groups') as batch_op:
        batch_op.alter_column('step_id', existing_type=sa.String(36), nullable=True)

    # 3. Add parent_action_id to actions for nested actions
    op.add_column(
        'tool_chain_actions',
        sa.Column('parent_action_id', sa.String(36), nullable=True)
    )
    op.create_index(
        'ix_tool_chain_actions_parent_action_id',
        'tool_chain_actions',
        ['parent_action_id']
    )

    # 4. Make step_id nullable in actions (nested actions don't have direct step_id)
    with op.batch_alter_table('tool_chain_actions') as batch_op:
        batch_op.alter_column('step_id', existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    # Reverse order of operations

    # 4. Make step_id NOT NULL in actions (will fail if NULL values exist)
    with op.batch_alter_table('tool_chain_actions') as batch_op:
        batch_op.alter_column('step_id', existing_type=sa.String(36), nullable=False)

    # 3. Remove parent_action_id from actions
    op.drop_index('ix_tool_chain_actions_parent_action_id', 'tool_chain_actions')
    with op.batch_alter_table('tool_chain_actions') as batch_op:
        batch_op.drop_column('parent_action_id')

    # 2. Make step_id NOT NULL in condition_groups (will fail if NULL values exist)
    with op.batch_alter_table('tool_chain_condition_groups') as batch_op:
        batch_op.alter_column('step_id', existing_type=sa.String(36), nullable=False)

    # 1. Remove action_id from condition_groups
    op.drop_index('ix_tool_chain_condition_groups_action_id', 'tool_chain_condition_groups')
    with op.batch_alter_table('tool_chain_condition_groups') as batch_op:
        batch_op.drop_column('action_id')

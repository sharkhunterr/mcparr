"""Add tool calling fields to training prompts

Revision ID: 66c704a2b53f
Revises: e5f6a7b8c9d0
Create Date: 2025-12-09 11:17:32.766333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66c704a2b53f'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (SQLite compatible)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('training_prompts', 'tool_call'):
        op.add_column('training_prompts', sa.Column('tool_call', sa.JSON(), nullable=True))

    if not column_exists('training_prompts', 'tool_response'):
        op.add_column('training_prompts', sa.Column('tool_response', sa.JSON(), nullable=True))

    if not column_exists('training_prompts', 'assistant_response'):
        op.add_column('training_prompts', sa.Column('assistant_response', sa.Text(), nullable=True))


def downgrade() -> None:
    if column_exists('training_prompts', 'assistant_response'):
        op.drop_column('training_prompts', 'assistant_response')

    if column_exists('training_prompts', 'tool_response'):
        op.drop_column('training_prompts', 'tool_response')

    if column_exists('training_prompts', 'tool_call'):
        op.drop_column('training_prompts', 'tool_call')

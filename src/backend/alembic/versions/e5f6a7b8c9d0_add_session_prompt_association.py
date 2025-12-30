"""Add session_prompt_association table for many-to-many relationship

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the association table for many-to-many relationship
    op.create_table(
        'session_prompt_association',
        sa.Column('session_id', sa.String(36), sa.ForeignKey('training_sessions.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('prompt_id', sa.String(36), sa.ForeignKey('training_prompts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
    )

    # Migrate existing session_id relationships to the new association table
    # This preserves existing prompt-session associations
    op.execute("""
        INSERT INTO session_prompt_association (session_id, prompt_id, added_at)
        SELECT session_id, id, updated_at
        FROM training_prompts
        WHERE session_id IS NOT NULL
    """)


def downgrade() -> None:
    # Note: Downgrade will lose many-to-many associations that can't be represented in one-to-many
    op.drop_table('session_prompt_association')

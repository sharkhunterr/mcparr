"""Add training_backend column to training_sessions

Revision ID: d4e5f6a7b8c9
Revises: fc44cc5970f9
Create Date: 2025-12-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'fc44cc5970f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add training_backend column with default value 'ollama_modelfile'
    op.add_column(
        'training_sessions',
        sa.Column('training_backend', sa.String(50), nullable=False, server_default='ollama_modelfile')
    )


def downgrade() -> None:
    op.drop_column('training_sessions', 'training_backend')

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


def upgrade() -> None:
    # Add external_url column to service_configs table
    op.add_column('service_configs', sa.Column('external_url', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove external_url column from service_configs table
    op.drop_column('service_configs', 'external_url')

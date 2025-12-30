"""Add group tables for access control

Revision ID: a1b2c3d4e5f6
Revises: 38ec2f63fe33
Create Date: 2025-12-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '38ec2f63fe33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create groups table
    op.create_table(
        'groups',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=True, default='#6366f1'),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create group_memberships table
    op.create_table(
        'group_memberships',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('groups.id'), nullable=False, index=True),
        sa.Column('central_user_id', sa.String(100), nullable=False, index=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('granted_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create group_tool_permissions table
    op.create_table(
        'group_tool_permissions',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('groups.id'), nullable=False, index=True),
        sa.Column('tool_name', sa.String(200), nullable=False, index=True),
        sa.Column('service_type', sa.String(50), nullable=True, index=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create default Admin group with all permissions
    from datetime import datetime
    from uuid import uuid4

    admin_group_id = str(uuid4())
    now = datetime.utcnow()

    op.execute(
        f"""
        INSERT INTO groups (id, name, description, color, icon, priority, is_system, enabled, created_at, updated_at)
        VALUES ('{admin_group_id}', 'Admin', 'Administrators with full access to all tools', '#ef4444', 'shield', 100, 1, 1, '{now.isoformat()}', '{now.isoformat()}')
        """
    )

    # Add wildcard permission for Admin group (all tools)
    admin_perm_id = str(uuid4())
    op.execute(
        f"""
        INSERT INTO group_tool_permissions (id, group_id, tool_name, service_type, enabled, description, created_at, updated_at)
        VALUES ('{admin_perm_id}', '{admin_group_id}', '*', NULL, 1, 'Full access to all tools', '{now.isoformat()}', '{now.isoformat()}')
        """
    )


def downgrade() -> None:
    op.drop_table('group_tool_permissions')
    op.drop_table('group_memberships')
    op.drop_table('groups')

"""Add training session and prompt tables

Revision ID: fc44cc5970f9
Revises: a1b2c3d4e5f6
Create Date: 2025-12-01 09:06:16.552199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc44cc5970f9'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create training_sessions table
    op.create_table(
        'training_sessions',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('base_model', sa.String(100), nullable=False, index=True),
        sa.Column('output_model', sa.String(100), nullable=True),
        sa.Column('training_type', sa.String(20), nullable=False, default='fine_tune'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('current_epoch', sa.Integer, nullable=False, default=0),
        sa.Column('total_epochs', sa.Integer, nullable=False, default=1),
        sa.Column('current_step', sa.Integer, nullable=False, default=0),
        sa.Column('total_steps', sa.Integer, nullable=False, default=0),
        sa.Column('progress_percent', sa.Float, nullable=False, default=0.0),
        sa.Column('loss', sa.Float, nullable=True),
        sa.Column('learning_rate', sa.Float, nullable=True),
        sa.Column('metrics_history', sa.JSON, nullable=False, default=[]),
        sa.Column('hyperparameters', sa.JSON, nullable=False, default={}),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('estimated_completion', sa.DateTime, nullable=True),
        sa.Column('gpu_memory_used', sa.Float, nullable=True),
        sa.Column('cpu_usage', sa.Float, nullable=True),
        sa.Column('dataset_size', sa.Integer, nullable=False, default=0),
        sa.Column('dataset_path', sa.String(500), nullable=True),
        sa.Column('ollama_service_id', sa.String(36), sa.ForeignKey('service_configs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # Create training_prompts table
    op.create_table(
        'training_prompts',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=False, default='general', index=True),
        sa.Column('difficulty', sa.String(20), nullable=False, default='basic'),
        sa.Column('source', sa.String(20), nullable=False, default='manual'),
        sa.Column('format', sa.String(20), nullable=False, default='chat'),
        sa.Column('content', sa.JSON, nullable=False),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('user_input', sa.Text, nullable=False),
        sa.Column('expected_output', sa.Text, nullable=False),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('is_validated', sa.Boolean, nullable=False, default=False),
        sa.Column('validation_score', sa.Float, nullable=True),
        sa.Column('validated_at', sa.DateTime, nullable=True),
        sa.Column('validated_by', sa.String(100), nullable=True),
        sa.Column('times_used', sa.Integer, nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('training_sessions.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('system_template', sa.Text, nullable=True),
        sa.Column('user_template', sa.Text, nullable=False),
        sa.Column('assistant_template', sa.Text, nullable=False),
        sa.Column('variables', sa.JSON, nullable=False, default=[]),
        sa.Column('category', sa.String(50), nullable=False, default='general'),
        sa.Column('format', sa.String(20), nullable=False, default='chat'),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('times_used', sa.Integer, nullable=False, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('prompt_templates')
    op.drop_table('training_prompts')
    op.drop_table('training_sessions')

"""Add shareable report links table for public report sharing

Revision ID: 20250227_000002
Revises: 20250227_000001
Create Date: 2025-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250227_000002'
down_revision: Union[str, None] = '20250227_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create shareable_report_links table
    op.create_table(
        'shareable_report_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_prefix', sa.String(16), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_shareable_report_links_token_hash', 'shareable_report_links', ['token_hash'], unique=True)
    op.create_index('ix_shareable_report_links_report_id', 'shareable_report_links', ['report_id'])
    op.create_index('ix_shareable_report_links_user_id', 'shareable_report_links', ['user_id'])
    op.create_index('ix_shareable_report_links_expires_at', 'shareable_report_links', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_shareable_report_links_expires_at')
    op.drop_index('ix_shareable_report_links_user_id')
    op.drop_index('ix_shareable_report_links_report_id')
    op.drop_index('ix_shareable_report_links_token_hash')
    op.drop_table('shareable_report_links')

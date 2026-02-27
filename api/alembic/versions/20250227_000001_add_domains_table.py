"""Add domains table for bulk domain management

Revision ID: 20250227_000001
Revises: 20250225_000001
Create Date: 2025-02-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250227_000001'
down_revision: Union[str, None] = '20250225_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create domain status enum
    domain_status = postgresql.ENUM('pending', 'verified', 'unverified', name='domainstatus', create_type=False)
    domain_status.create(op.get_bind(), checkfirst=True)

    # Create domains table
    op.create_table(
        'domains',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'verified', 'unverified', name='domainstatus', create_type=False),
                  nullable=False, server_default='pending'),
        sa.Column('verification_token', sa.String(64), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('total_scans', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_scan_at', sa.DateTime(), nullable=True),
        sa.Column('last_score', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_domains_user_id', 'domains', ['user_id'])
    op.create_index('ix_domains_domain', 'domains', ['domain'])
    op.create_index('ix_domains_user_domain', 'domains', ['user_id', 'domain'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_domains_user_domain')
    op.drop_index('ix_domains_domain')
    op.drop_index('ix_domains_user_id')
    op.drop_table('domains')
    op.execute("DROP TYPE IF EXISTS domainstatus")

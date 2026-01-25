"""Initial schema - Users, Scans, Pages, Issues

Revision ID: 20250125_000001
Revises:
Create Date: 2025-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250125_000001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE plantype AS ENUM ('free', 'starter', 'professional', 'agency', 'enterprise')")
    op.execute("CREATE TYPE scanstatus AS ENUM ('queued', 'crawling', 'scanning', 'processing', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE impactlevel AS ENUM ('critical', 'serious', 'moderate', 'minor')")
    op.execute("CREATE TYPE wcaglevel AS ENUM ('A', 'AA', 'AAA')")

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('plan', postgresql.ENUM('free', 'starter', 'professional', 'agency', 'enterprise', name='plantype', create_type=False), nullable=False, server_default='free'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create scans table
    op.create_table(
        'scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('crawl', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('max_pages', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', postgresql.ENUM('queued', 'crawling', 'scanning', 'processing', 'completed', 'failed', 'cancelled', name='scanstatus', create_type=False), nullable=False, server_default='queued'),
        sa.Column('progress_stage', sa.String(50), nullable=True),
        sa.Column('progress_current', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('pages_scanned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('issues_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('issues_critical', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('issues_serious', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('issues_moderate', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('issues_minor', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_scans_user_id', 'scans', ['user_id'])
    op.create_index('ix_scans_status', 'scans', ['status'])
    op.create_index('ix_scans_created_at', 'scans', ['created_at'])

    # Create pages table
    op.create_table(
        'pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('title', sa.String(512), nullable=True),
        sa.Column('depth', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('issues_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_rules', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_rules', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('incomplete_rules', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('load_time_ms', sa.Integer(), nullable=True),
        sa.Column('scan_time_ms', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('scanned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_pages_scan_id', 'pages', ['scan_id'])

    # Create issues table
    op.create_table(
        'issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('impact', postgresql.ENUM('critical', 'serious', 'moderate', 'minor', name='impactlevel', create_type=False), nullable=False),
        sa.Column('wcag_criteria', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('wcag_level', postgresql.ENUM('A', 'AA', 'AAA', name='wcaglevel', create_type=False), nullable=True),
        sa.Column('bfsg_reference', sa.String(255), nullable=True),
        sa.Column('title_de', sa.String(500), nullable=False),
        sa.Column('description_de', sa.Text(), nullable=True),
        sa.Column('fix_suggestion_de', sa.Text(), nullable=True),
        sa.Column('element_selector', sa.Text(), nullable=True),
        sa.Column('element_html', sa.Text(), nullable=True),
        sa.Column('element_xpath', sa.Text(), nullable=True),
        sa.Column('help_url', sa.String(2048), nullable=True),
        sa.Column('screenshot_path', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_issues_page_id', 'issues', ['page_id'])
    op.create_index('ix_issues_rule_id', 'issues', ['rule_id'])
    op.create_index('ix_issues_impact', 'issues', ['impact'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('issues')
    op.drop_table('pages')
    op.drop_table('scans')
    op.drop_table('users')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS wcaglevel")
    op.execute("DROP TYPE IF EXISTS impactlevel")
    op.execute("DROP TYPE IF EXISTS scanstatus")
    op.execute("DROP TYPE IF EXISTS plantype")

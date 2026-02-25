"""Add indexes for issues table query optimization

Revision ID: 20250225_000001
Revises: 20250217_000001
Create Date: 2025-02-25

This migration adds composite indexes to improve query performance for:
- Filtering issues by page_id and impact (common in scan results)
- Filtering issues by page_id and WCAG level
- URL-based scan lookups for comparison features
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20250225_000001'
down_revision: Union[str, None] = '20250217_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for filtering issues by page and impact level
    # Used when viewing scan results filtered by severity
    op.create_index(
        'ix_issues_page_id_impact',
        'issues',
        ['page_id', 'impact']
    )

    # Composite index for filtering issues by page and WCAG level
    # Used when filtering issues by WCAG compliance level
    op.create_index(
        'ix_issues_page_id_wcag_level',
        'issues',
        ['page_id', 'wcag_level']
    )

    # Index for scan URL lookups (used in scan comparison)
    # Partial index for completed scans only since comparisons are for completed scans
    op.create_index(
        'ix_scans_url_completed',
        'scans',
        ['url', 'completed_at'],
        postgresql_where="status = 'completed'"
    )

    # Index for pages by scan_id and score (used in reports and summaries)
    op.create_index(
        'ix_pages_scan_id_score',
        'pages',
        ['scan_id', 'score']
    )


def downgrade() -> None:
    op.drop_index('ix_pages_scan_id_score', 'pages')
    op.drop_index('ix_scans_url_completed', 'scans')
    op.drop_index('ix_issues_page_id_wcag_level', 'issues')
    op.drop_index('ix_issues_page_id_impact', 'issues')

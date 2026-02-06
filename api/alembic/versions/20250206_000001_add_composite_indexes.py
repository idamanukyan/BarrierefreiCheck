"""Add composite indexes for common query patterns

Revision ID: 20250206_000001
Revises: 20250125_000001
Create Date: 2025-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20250206_000001'
down_revision: Union[str, None] = '20250125_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for user's scans by status (common dashboard query)
    op.create_index(
        'ix_scans_user_id_status',
        'scans',
        ['user_id', 'status']
    )

    # Composite index for user's scans by creation date (listing with sorting)
    op.create_index(
        'ix_scans_user_id_created_at',
        'scans',
        ['user_id', 'created_at']
    )

    # Index for completed scans with scores (dashboard stats)
    op.create_index(
        'ix_scans_status_score',
        'scans',
        ['status', 'score'],
        postgresql_where="status = 'completed' AND score IS NOT NULL"
    )

    # Index for scan completion date (score history query)
    op.create_index(
        'ix_scans_completed_at',
        'scans',
        ['completed_at'],
        postgresql_where="completed_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index('ix_scans_completed_at', 'scans')
    op.drop_index('ix_scans_status_score', 'scans')
    op.drop_index('ix_scans_user_id_created_at', 'scans')
    op.drop_index('ix_scans_user_id_status', 'scans')

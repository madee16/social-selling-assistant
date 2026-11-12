"""drop wati columns from widget_settings

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-11 21:30:00.000000

Removes the unused WATI integration columns (wati_enabled, wati_endpoint_url,
wati_access_token). The integration is no longer supported; WhatsApp now runs
exclusively through the Meta Cloud API.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE widget_settings DROP COLUMN IF EXISTS wati_access_token")
    op.execute("ALTER TABLE widget_settings DROP COLUMN IF EXISTS wati_endpoint_url")
    op.execute("ALTER TABLE widget_settings DROP COLUMN IF EXISTS wati_enabled")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('widget_settings', sa.Column('wati_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('widget_settings', sa.Column('wati_endpoint_url', sa.String(length=500), nullable=True))
    op.add_column('widget_settings', sa.Column('wati_access_token', sa.Text(), nullable=True))
    op.execute("UPDATE widget_settings SET wati_enabled = false WHERE wati_enabled IS NULL")
    op.alter_column('widget_settings', 'wati_enabled', nullable=False)

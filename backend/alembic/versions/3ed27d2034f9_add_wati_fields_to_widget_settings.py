"""add_wati_fields_to_widget_settings

Revision ID: 3ed27d2034f9
Revises: efd38167bc52
Create Date: 2026-07-29 23:07:12.616563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ed27d2034f9'
down_revision: Union[str, Sequence[str], None] = 'efd38167bc52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('widget_settings', sa.Column('wati_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('widget_settings', sa.Column('wati_endpoint_url', sa.String(length=500), nullable=True))
    op.add_column('widget_settings', sa.Column('wati_access_token', sa.String(length=2000), nullable=True))
    op.execute("UPDATE widget_settings SET wati_enabled = false WHERE wati_enabled IS NULL")
    op.alter_column('widget_settings', 'wati_enabled', nullable=False)


def downgrade() -> None:
    op.drop_column('widget_settings', 'wati_access_token')
    op.drop_column('widget_settings', 'wati_endpoint_url')
    op.drop_column('widget_settings', 'wati_enabled')

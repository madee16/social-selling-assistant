"""widen integration token columns to text for encrypted storage

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-11 21:30:00.000000

Fernet ciphertext is longer than the plaintext token, so the WhatsApp,
Messenger and WATI token columns must hold text (and surface overflow).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE widget_settings ALTER COLUMN whatsapp_access_token TYPE text")
    op.execute("ALTER TABLE widget_settings ALTER COLUMN messenger_access_token TYPE text")
    op.execute("ALTER TABLE widget_settings ALTER COLUMN wati_access_token TYPE text")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE widget_settings ALTER COLUMN whatsapp_access_token TYPE varchar(500)")
    op.execute("ALTER TABLE widget_settings ALTER COLUMN messenger_access_token TYPE varchar(500)")
    op.execute("ALTER TABLE widget_settings ALTER COLUMN wati_access_token TYPE varchar(2000)")

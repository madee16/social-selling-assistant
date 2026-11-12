"""unique partial index on conversations (user_id, platform, platform_conversation_id)

Revision ID: a7b9c1d2e3f4
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-05 21:00:00.000000

Prevents duplicate conversations created by concurrent webhook deliveries
and double-fired webhooks for the same platform channel.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7b9c1d2e3f4'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_conversations_user_platform_pci
        ON conversations (user_id, platform, platform_conversation_id)
        WHERE platform IS NOT NULL AND platform_conversation_id IS NOT NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DROP INDEX IF EXISTS ix_conversations_user_platform_pci"
    )
"""add indexes on products.category_id and order_items.product_id

Revision ID: b1c2d3e4f5a6
Revises: a7b9c1d2e3f4
Create Date: 2026-10-11 21:00:00.000000

Speeds up category filtering of products and the product<->order_item joins
used by analytics and product order history.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a7b9c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_category_id ON products (category_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_order_items_product_id ON order_items (product_id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_order_items_product_id")
    op.execute("DROP INDEX IF EXISTS ix_products_category_id")

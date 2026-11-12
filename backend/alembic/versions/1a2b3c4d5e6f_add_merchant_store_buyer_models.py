"""add_merchant_store_buyer_models

Revision ID: 1a2b3c4d5e6f
Revises: efd38167bc52
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '3ed27d2034f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to pre-existing tables
    # FK constraints + indexes are created AFTER the new tables below
    # (Postgres requires the referenced tables to already exist).
    # categories: ['store_id']
    op.add_column('categories', sa.Column('store_id', sa.UUID()))

    # products: ['store_id']
    op.add_column('products', sa.Column('store_id', sa.UUID()))

    # orders: ['buyer_id', 'store_id']
    op.add_column('orders', sa.Column('buyer_id', sa.UUID()))
    op.add_column('orders', sa.Column('store_id', sa.UUID()))

    # conversations: ['buyer_id', 'store_id']
    op.add_column('conversations', sa.Column('buyer_id', sa.UUID()))
    op.add_column('conversations', sa.Column('store_id', sa.UUID()))

    # notifications: ['buyer_id', 'store_id']
    op.add_column('notifications', sa.Column('buyer_id', sa.UUID()))
    op.add_column('notifications', sa.Column('store_id', sa.UUID()))

    # widget_settings: ['merchant_id', 'store_id']
    op.add_column('widget_settings', sa.Column('merchant_id', sa.UUID()))
    op.add_column('widget_settings', sa.Column('store_id', sa.UUID()))


    # Create new tables
    # merchants
    op.create_table('merchants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('trust_score_ref', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_merchants_user_id'), 'merchants', ['user_id'], unique=False)

    # stores
    op.create_table('stores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=500)),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_stores_merchant_id'), 'stores', ['merchant_id'], unique=False)

    # store_members
    op.create_table('store_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_store_members_store_id'), 'store_members', ['store_id'], unique=False)
    op.create_index(op.f('ix_store_members_user_id'), 'store_members', ['user_id'], unique=False)

    # buyers
    op.create_table('buyers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), unique=True),
        sa.Column('phone', sa.String(length=50)),
        sa.Column('name', sa.String(length=255)),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # attribute_defs
    op.create_table('attribute_defs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('attribute_type', sa.String(length=50), nullable=False),
        sa.Column('values', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('is_required', sa.Boolean(), nullable=False),
        sa.Column('is_filterable', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_attribute_defs_merchant_id'), 'attribute_defs', ['merchant_id'], unique=False)

    # product_attributes
    op.create_table('product_attributes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('attribute_def_id', sa.UUID(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['attribute_def_id'], ['attribute_defs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_product_attributes_product_id'), 'product_attributes', ['product_id'], unique=False)
    op.create_index(op.f('ix_product_attributes_attribute_def_id'), 'product_attributes', ['attribute_def_id'], unique=False)

    # product_variants
    op.create_table('product_variants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('sku', sa.String(length=255), unique=True),
        sa.Column('name', sa.String(length=255)),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_product_variants_product_id'), 'product_variants', ['product_id'], unique=False)

    # inventory
    op.create_table('inventory',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False),
        sa.Column('low_stock_threshold', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_product_id'), 'inventory', ['product_id'], unique=False)
    op.create_index(op.f('ix_inventory_store_id'), 'inventory', ['store_id'], unique=False)

    # prices
    op.create_table('prices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('sale_price', sa.Float()),
        sa.Column('effective_from', sa.DateTime(timezone=False)),
        sa.Column('effective_to', sa.DateTime(timezone=False)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_prices_product_id'), 'prices', ['product_id'], unique=False)
    op.create_index(op.f('ix_prices_store_id'), 'prices', ['store_id'], unique=False)

    # seo_data
    op.create_table('seo_data',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255)),
        sa.Column('description', sa.String()),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('slug', sa.String(length=255)),
        sa.Column('canonical_url', sa.String(length=500)),
        sa.Column('is_indexable', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # seo_scores
    op.create_table('seo_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('seo_data_id', sa.UUID(), nullable=False),
        sa.Column('overall_score', sa.Float()),
        sa.Column('keyword_score', sa.Float()),
        sa.Column('meta_score', sa.Float()),
        sa.Column('structure_score', sa.Float()),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('calculated_at', sa.DateTime(timezone=False)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['seo_data_id'], ['seo_data.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_seo_scores_seo_data_id'), 'seo_scores', ['seo_data_id'], unique=False)

    # ai_sessions
    op.create_table('ai_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID()),
        sa.Column('buyer_id', sa.UUID()),
        sa.Column('intent', sa.String(length=100)),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('conversation_summary', sa.String()),
        sa.Column('total_messages', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['buyer_id'], ['buyers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_sessions_buyer_id'), 'ai_sessions', ['buyer_id'], unique=False)
    op.create_index(op.f('ix_ai_sessions_store_id'), 'ai_sessions', ['store_id'], unique=False)

    # ai_messages
    op.create_table('ai_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('confidence', sa.Float()),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['session_id'], ['ai_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_messages_session_id'), 'ai_messages', ['session_id'], unique=False)

    # ai_tool_calls
    op.create_table('ai_tool_calls',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('arguments', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['message_id'], ['ai_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_tool_calls_session_id'), 'ai_tool_calls', ['session_id'], unique=False)
    op.create_index(op.f('ix_ai_tool_calls_message_id'), 'ai_tool_calls', ['message_id'], unique=False)

    # approvals
    op.create_table('approvals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('approval_type', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(length=255)),
        sa.Column('description', sa.String()),
        sa.Column('requester_id', sa.UUID(), nullable=False),
        sa.Column('approver_id', sa.UUID()),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('rejection_reason', sa.String()),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # automation_rules
    op.create_table('automation_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('execution_count', sa.Integer(), nullable=False),
        sa.Column('last_executed_at', sa.DateTime(timezone=False)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_automation_rules_merchant_id'), 'automation_rules', ['merchant_id'], unique=False)

    # consent_records
    op.create_table('consent_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('buyer_id', sa.UUID(), nullable=False),
        sa.Column('consent_type', sa.String(length=100), nullable=False),
        sa.Column('consent_text', sa.String()),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['buyer_id'], ['buyers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_consent_records_buyer_id'), 'consent_records', ['buyer_id'], unique=False)

    # audit_logs
    op.create_table('audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID()),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100)),
        sa.Column('entity_id', sa.String()),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('ip_address', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # events
    op.create_table('events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100)),
        sa.Column('entity_id', sa.String()),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # event_collections
    op.create_table('event_collections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('collection_type', sa.String(length=100), nullable=False),
        sa.Column('collection_id', sa.String(), nullable=False),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_event_collections_event_id'), 'event_collections', ['event_id'], unique=False)

    # event_product_gaps
    op.create_table('event_product_gaps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_collection_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('gap_type', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_collection_id'], ['event_collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_event_product_gaps_product_id'), 'event_product_gaps', ['product_id'], unique=False)
    op.create_index(op.f('ix_event_product_gaps_event_collection_id'), 'event_product_gaps', ['event_collection_id'], unique=False)

    # collections
    op.create_table('collections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID()),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False, unique=True),
        sa.Column('description', sa.String()),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_visible', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_collections_merchant_id'), 'collections', ['merchant_id'], unique=False)

    # marketplace_listings
    op.create_table('marketplace_listings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID(), nullable=False),
        sa.Column('marketplace', sa.String(length=100), nullable=False),
        sa.Column('marketplace_product_id', sa.String(length=255)),
        sa.Column('listing_status', sa.String(length=20), nullable=False),
        sa.Column('sync_status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_marketplace_listings_product_id'), 'marketplace_listings', ['product_id'], unique=False)
    op.create_index(op.f('ix_marketplace_listings_store_id'), 'marketplace_listings', ['store_id'], unique=False)

    # product_scores
    op.create_table('product_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('store_id', sa.UUID(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('score_type', sa.String(length=50), nullable=False),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('calculated_at', sa.DateTime(timezone=False)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_product_scores_store_id'), 'product_scores', ['store_id'], unique=False)
    op.create_index(op.f('ix_product_scores_product_id'), 'product_scores', ['product_id'], unique=False)

    # seller_trust_scores
    op.create_table('seller_trust_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('seller_id', sa.UUID(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('components', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=False)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['seller_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_seller_trust_scores_seller_id'), 'seller_trust_scores', ['seller_id'], unique=False)

    # Add FK constraints + indexes linking the pre-existing tables to the new tables
    op.create_foreign_key(None, 'categories', 'stores', ['store_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_categories_store_id'), 'categories', ['store_id'], unique=False)

    op.create_foreign_key(None, 'products', 'stores', ['store_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_products_store_id'), 'products', ['store_id'], unique=False)

    op.create_foreign_key(None, 'orders', 'buyers', ['buyer_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_orders_buyer_id'), 'orders', ['buyer_id'], unique=False)
    op.create_foreign_key(None, 'orders', 'stores', ['store_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_orders_store_id'), 'orders', ['store_id'], unique=False)

    op.create_foreign_key(None, 'conversations', 'buyers', ['buyer_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_conversations_buyer_id'), 'conversations', ['buyer_id'], unique=False)
    op.create_foreign_key(None, 'conversations', 'stores', ['store_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_conversations_store_id'), 'conversations', ['store_id'], unique=False)

    op.create_foreign_key(None, 'notifications', 'buyers', ['buyer_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_notifications_buyer_id'), 'notifications', ['buyer_id'], unique=False)
    op.create_foreign_key(None, 'notifications', 'stores', ['store_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_notifications_store_id'), 'notifications', ['store_id'], unique=False)

    op.create_foreign_key(None, 'widget_settings', 'merchants', ['merchant_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_widget_settings_merchant_id'), 'widget_settings', ['merchant_id'], unique=False)
    op.create_foreign_key(None, 'widget_settings', 'stores', ['store_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_widget_settings_store_id'), 'widget_settings', ['store_id'], unique=False)



def downgrade() -> None:
    # Drop new columns from pre-existing tables
    op.drop_index(op.f('ix_widget_settings_store_id'), table_name='widget_settings')
    op.drop_constraint(None, 'widget_settings', type_='foreignkey')
    op.drop_column('widget_settings', 'store_id')
    op.drop_index(op.f('ix_widget_settings_merchant_id'), table_name='widget_settings')
    op.drop_constraint(None, 'widget_settings', type_='foreignkey')
    op.drop_column('widget_settings', 'merchant_id')
    op.drop_index(op.f('ix_notifications_store_id'), table_name='notifications')
    op.drop_constraint(None, 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'store_id')
    op.drop_index(op.f('ix_notifications_buyer_id'), table_name='notifications')
    op.drop_constraint(None, 'notifications', type_='foreignkey')
    op.drop_column('notifications', 'buyer_id')
    op.drop_index(op.f('ix_conversations_store_id'), table_name='conversations')
    op.drop_constraint(None, 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'store_id')
    op.drop_index(op.f('ix_conversations_buyer_id'), table_name='conversations')
    op.drop_constraint(None, 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'buyer_id')
    op.drop_index(op.f('ix_orders_store_id'), table_name='orders')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.drop_column('orders', 'store_id')
    op.drop_index(op.f('ix_orders_buyer_id'), table_name='orders')
    op.drop_constraint(None, 'orders', type_='foreignkey')
    op.drop_column('orders', 'buyer_id')
    op.drop_index(op.f('ix_products_store_id'), table_name='products')
    op.drop_constraint(None, 'products', type_='foreignkey')
    op.drop_column('products', 'store_id')
    op.drop_index(op.f('ix_categories_store_id'), table_name='categories')
    op.drop_constraint(None, 'categories', type_='foreignkey')
    op.drop_column('categories', 'store_id')

    # Drop new tables (reverse order)
    op.drop_index(op.f('ix_seller_trust_scores_seller_id'), table_name='seller_trust_scores')
    op.drop_table('seller_trust_scores')
    op.drop_index(op.f('ix_product_scores_product_id'), table_name='product_scores')
    op.drop_index(op.f('ix_product_scores_store_id'), table_name='product_scores')
    op.drop_table('product_scores')
    op.drop_index(op.f('ix_marketplace_listings_store_id'), table_name='marketplace_listings')
    op.drop_index(op.f('ix_marketplace_listings_product_id'), table_name='marketplace_listings')
    op.drop_table('marketplace_listings')
    op.drop_index(op.f('ix_collections_merchant_id'), table_name='collections')
    op.drop_table('collections')
    op.drop_index(op.f('ix_event_product_gaps_event_collection_id'), table_name='event_product_gaps')
    op.drop_index(op.f('ix_event_product_gaps_product_id'), table_name='event_product_gaps')
    op.drop_table('event_product_gaps')
    op.drop_index(op.f('ix_event_collections_event_id'), table_name='event_collections')
    op.drop_table('event_collections')
    op.drop_table('events')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_consent_records_buyer_id'), table_name='consent_records')
    op.drop_table('consent_records')
    op.drop_index(op.f('ix_automation_rules_merchant_id'), table_name='automation_rules')
    op.drop_table('automation_rules')
    op.drop_table('approvals')
    op.drop_index(op.f('ix_ai_tool_calls_message_id'), table_name='ai_tool_calls')
    op.drop_index(op.f('ix_ai_tool_calls_session_id'), table_name='ai_tool_calls')
    op.drop_table('ai_tool_calls')
    op.drop_index(op.f('ix_ai_messages_session_id'), table_name='ai_messages')
    op.drop_table('ai_messages')
    op.drop_index(op.f('ix_ai_sessions_store_id'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_buyer_id'), table_name='ai_sessions')
    op.drop_table('ai_sessions')
    op.drop_index(op.f('ix_seo_scores_seo_data_id'), table_name='seo_scores')
    op.drop_table('seo_scores')
    op.drop_table('seo_data')
    op.drop_index(op.f('ix_prices_store_id'), table_name='prices')
    op.drop_index(op.f('ix_prices_product_id'), table_name='prices')
    op.drop_table('prices')
    op.drop_index(op.f('ix_inventory_store_id'), table_name='inventory')
    op.drop_index(op.f('ix_inventory_product_id'), table_name='inventory')
    op.drop_table('inventory')
    op.drop_index(op.f('ix_product_variants_product_id'), table_name='product_variants')
    op.drop_table('product_variants')
    op.drop_index(op.f('ix_product_attributes_attribute_def_id'), table_name='product_attributes')
    op.drop_index(op.f('ix_product_attributes_product_id'), table_name='product_attributes')
    op.drop_table('product_attributes')
    op.drop_index(op.f('ix_attribute_defs_merchant_id'), table_name='attribute_defs')
    op.drop_table('attribute_defs')
    op.drop_table('buyers')
    op.drop_index(op.f('ix_store_members_user_id'), table_name='store_members')
    op.drop_index(op.f('ix_store_members_store_id'), table_name='store_members')
    op.drop_table('store_members')
    op.drop_index(op.f('ix_stores_merchant_id'), table_name='stores')
    op.drop_table('stores')
    op.drop_index(op.f('ix_merchants_user_id'), table_name='merchants')
    op.drop_table('merchants')


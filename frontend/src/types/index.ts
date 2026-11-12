export interface User {
  id: string;
  email: string;
  company_name: string;
  company_logo_url: string | null;
  phone: string | null;
  preferred_language: string;
  currency: string;
  notifications_enabled: boolean;
  ai_custom_instructions: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface Category {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string | null;
  price: number;
  category_id: string | null;
  image_url: string | null;
  stock_quantity: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Conversation {
  id: string;
  customer_name: string | null;
  customer_phone: string | null;
  customer_address: string | null;
  language: string | null;
  platform: string | null;
  platform_conversation_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  language: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string | null;
  product_name: string | null;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  id: string;
  user_id: string;
  conversation_id: string | null;
  customer_name: string;
  customer_phone: string | null;
  customer_address: string | null;
  status: string;
  total_amount: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface OrderCreateItem {
  product_id: string;
  quantity: number;
  unit_price: number;
}

export interface OrderCreate {
  conversation_id?: string;
  customer_name: string;
  customer_phone?: string;
  customer_address?: string;
  items: OrderCreateItem[];
}

export interface OrderListResponse {
  items: Order[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SalesMetrics {
  total_revenue: number;
  total_orders: number;
  avg_order_value: number;
  revenue_change: number;
  orders_change: number;
}

export interface TopProduct {
  product_id: string;
  name: string;
  total_quantity: number;
  total_revenue: number;
  order_count: number;
}

export interface OrderStatusDistribution {
  status: string;
  count: number;
  percentage: number;
}

export interface FunnelData {
  conversations: number;
  conversations_with_messages: number;
  orders_created: number;
  orders_completed: number;
  conversion_rate: number;
}

export interface CustomerMetrics {
  total_customers: number;
  new_customers: number;
  returning_customers: number;
  avg_order_value: number;
}

export interface RevenueSeriesPoint {
  date: string;
  revenue: number;
  orders: number;
}

export interface AnalyticsResponse {
  sales: SalesMetrics;
  top_products: TopProduct[];
  status_distribution: OrderStatusDistribution[];
  funnel: FunnelData;
  customers: CustomerMetrics;
  revenue_series: RevenueSeriesPoint[];
  period: string;
  date_range: { start: string; end: string };
}

export interface DateRangeParams {
  period?: 'day' | 'week' | 'month';
  days?: number;
  start_date?: string;
  end_date?: string;
}

export interface Merchant {
  id: string;
  user_id: string;
  company_name: string;
  verification_status: string;
  trust_score_ref: number | null;
  created_at: string;
}

export interface StoreSettings {
  currency?: string;
  timezone?: string;
  [key: string]: unknown;
}

export interface Store {
  id: string;
  merchant_id: string;
  slug: string;
  name: string;
  domain: string | null;
  settings: StoreSettings | null;
  status: string;
  created_at: string;
}

export interface StoreMember {
  id: string;
  store_id: string;
  user_id: string;
  role: string;
  created_at: string;
}

export interface StoreCreatePayload {
  name: string;
  slug: string;
  domain?: string;
  settings?: StoreSettings;
  status?: 'active' | 'inactive' | 'suspended';
}

export interface StoreUpdatePayload {
  name?: string;
  slug?: string;
  domain?: string;
  settings?: StoreSettings;
  status?: 'active' | 'inactive' | 'suspended';
}

export interface Buyer {
  id: string;
  email: string | null;
  phone: string | null;
  name: string | null;
  preferences: Record<string, unknown> | null;
  created_at: string;
}

export interface BuyerPayload {
  name?: string;
  email?: string;
  phone?: string;
  preferences?: Record<string, unknown>;
}

export interface ConsentRecord {
  id: string;
  buyer_id: string;
  consent_type: string;
  consent_text: string | null;
  granted: boolean;
  meta_data: Record<string, unknown> | null;
  created_at: string;
}

export interface ConsentRecordPayload {
  buyer_id: string;
  consent_type: string;
  consent_text?: string;
  granted?: boolean;
  meta_data?: Record<string, unknown>;
}

export interface Collection {
  id: string;
  merchant_id: string;
  store_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  sort_order: number;
  is_visible: boolean;
  created_at: string;
  updated_at: string;
}

export interface CollectionPayload {
  name: string;
  slug?: string;
  store_id?: string;
  description?: string;
  sort_order?: number;
  is_visible?: boolean;
}

export interface AttributeDef {
  id: string;
  merchant_id: string;
  name: string;
  attribute_type: string;
  values: string[] | null;
  is_required: boolean;
  is_filterable: boolean;
  sort_order: number;
  created_at: string;
}

export interface AttributeDefPayload {
  name: string;
  attribute_type: 'text' | 'number' | 'boolean' | 'select' | 'multi_select';
  values?: string[];
  is_required?: boolean;
  is_filterable?: boolean;
  sort_order?: number;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string | null;
  name: string | null;
  options: Record<string, unknown> | null;
  quantity: number;
  created_at: string;
}

export interface ProductVariantPayload {
  sku?: string;
  name?: string;
  options?: Record<string, unknown>;
  quantity?: number;
}

export interface InventoryRecord {
  id: string;
  product_id: string;
  store_id: string;
  quantity: number;
  reserved_quantity: number;
  low_stock_threshold: number;
  updated_at: string;
}

export interface InventoryPayload {
  store_id: string;
  quantity?: number;
  reserved_quantity?: number;
  low_stock_threshold?: number;
}

export interface Price {
  id: string;
  product_id: string;
  store_id: string;
  amount: number;
  currency: string;
  sale_price: number | null;
  effective_from: string | null;
  effective_to: string | null;
  created_at: string;
}

export interface PricePayload {
  store_id: string;
  amount: number;
  currency?: string;
  sale_price?: number;
  effective_from?: string;
  effective_to?: string;
}

export interface SeoData {
  id: string;
  entity_type: string;
  entity_id: string;
  title: string | null;
  description: string | null;
  keywords: string[] | null;
  slug: string | null;
  canonical_url: string | null;
  is_indexable: boolean;
  created_at: string;
  updated_at: string;
}

export interface SeoDataPayload {
  entity_type: string;
  entity_id: string;
  title?: string;
  description?: string;
  keywords?: string[];
  slug?: string;
  canonical_url?: string;
  is_indexable?: boolean;
}

export interface SeoScore {
  id: string;
  seo_data_id: string;
  overall_score: number | null;
  keyword_score: number | null;
  meta_score: number | null;
  structure_score: number | null;
  detail: Record<string, unknown> | null;
  calculated_at: string | null;
  created_at: string;
}

export interface SeoGenerateResponse {
  seo_data: SeoData;
  seo_score: SeoScore;
  message: string;
}


export interface MarketplaceListing {
  id: string;
  product_id: string;
  store_id: string;
  marketplace: string;
  marketplace_product_id: string | null;
  listing_status: string;
  sync_status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarketplaceListingPayload {
  store_id: string;
  marketplace: string;
  marketplace_product_id?: string;
  listing_status?: 'draft' | 'active' | 'inactive' | 'archived';
  sync_status?: 'pending' | 'synced' | 'failed';
  error_message?: string;
}

export interface ProductScore {
  id: string;
  product_id: string;
  store_id: string;
  score: number;
  score_type: string;
  detail: Record<string, unknown> | null;
  calculated_at: string | null;
  created_at: string;
}

export interface ProductScorePayload {
  store_id: string;
  score: number;
  score_type?: string;
  detail?: Record<string, unknown>;
}

export interface SellerTrustScore {
  id: string;
  seller_id: string;
  score: number;
  components: Record<string, unknown> | null;
  level: string;
  calculated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SellerTrustPayload {
  score: number;
  components?: Record<string, unknown>;
  level?: string;
}

export interface Approval {
  id: string;
  approval_type: string;
  entity_type: string;
  entity_id: string;
  title: string | null;
  description: string | null;
  requester_id: string;
  approver_id: string | null;
  status: string;
  rejection_reason: string | null;
  meta_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalPayload {
  approval_type: string;
  entity_type: string;
  entity_id: string;
  title?: string;
  description?: string;
  approver_id?: string;
  status?: 'pending' | 'approved' | 'rejected' | 'cancelled';
  meta_data?: Record<string, unknown>;
}

export interface AutomationRule {
  id: string;
  merchant_id: string;
  name: string;
  description: string | null;
  event_type: string;
  conditions: Record<string, unknown> | null;
  actions: Record<string, unknown> | null;
  is_active: boolean;
  priority: number;
  execution_count: number;
  last_executed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRulePayload {
  name: string;
  event_type: string;
  description?: string;
  conditions?: Record<string, unknown>;
  actions?: Record<string, unknown>;
  is_active?: boolean;
  priority?: number;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface EventRecord {
  id: string;
  event_type: string;
  entity_type: string | null;
  entity_id: string | null;
  payload: Record<string, unknown> | null;
  meta_data: Record<string, unknown> | null;
  created_at: string;
}

export interface EventPayload {
  event_type: 'holiday' | 'season' | 'campaign' | 'sale' | 'custom';
  entity_type?: string;
  entity_id?: string;
  payload?: Record<string, unknown>;
  meta_data?: Record<string, unknown>;
}

export interface AISession {
  id: string;
  store_id: string | null;
  buyer_id: string | null;
  intent: string | null;
  status: string;
  conversation_summary: string | null;
  total_messages: number;
  created_at: string;
  updated_at: string;
}

export interface AISessionPayload {
  store_id?: string;
  buyer_id?: string;
  intent?: string;
  status?: 'active' | 'closed' | 'escalated';
  conversation_summary?: string;
}

export interface AIMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  tool_calls: Record<string, unknown> | null;
  confidence: number | null;
  sequence: number;
  created_at: string;
}

export interface AIToolCall {
  id: string;
  session_id: string;
  message_id: string;
  tool_name: string;
  arguments: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  status: string;
  created_at: string;
}

export interface WidgetSettings {
  id: string;
  user_id: string;
  enabled: boolean;
  title: string;
  greeting: string;
  primary_color: string;
  position: string;
  show_branding: boolean;
  allowed_domains: string[] | null;
  whatsapp_phone_number_id: string | null;
  whatsapp_access_token: string | null;
  messenger_page_id: string | null;
  messenger_access_token: string | null;
  webhook_verify_token: string;
  created_at: string;
  updated_at: string;
}

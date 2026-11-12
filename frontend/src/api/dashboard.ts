import client from './client';

export interface DashboardData {
  total_conversations: number;
  total_orders: number;
  total_products: number;
  total_stores: number;
  total_collections: number;
  total_attribute_defs: number;
  total_buyers: number;
  pending_approvals: number;
  active_ai_sessions: number;
}

export interface ActivityItem {
  type: 'order_created' | 'conversation_started';
  customer_name: string;
  detail: string | null;
  timestamp: string;
}

export interface ActivityResponse {
  items: ActivityItem[];
}

export async function getDashboard(): Promise<DashboardData> {
  const { data } = await client.get('/api/dashboard');
  return data;
}

export async function getActivity(limit = 10): Promise<ActivityResponse> {
  const { data } = await client.get('/api/dashboard/activity', { params: { limit } });
  return data;
}

import client from './client';
import type { Order, OrderCreate, OrderListResponse } from '../types';

export async function listOrders(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<OrderListResponse> {
  const { data } = await client.get('/api/orders', { params });
  return data;
}

export async function getOrder(id: string): Promise<Order> {
  const { data } = await client.get(`/api/orders/${id}`);
  return data;
}

export async function createOrder(payload: OrderCreate): Promise<Order> {
  const { data } = await client.post('/api/orders', payload);
  return data;
}

export async function updateOrderStatus(id: string, status: string): Promise<Order> {
  const { data } = await client.patch(`/api/orders/${id}/status`, { status });
  return data;
}

export async function deleteOrder(id: string): Promise<void> {
  await client.delete(`/api/orders/${id}`);
}

export async function downloadOrderInvoicePdf(orderId: string): Promise<void> {
  const response = await client.get(`/api/orders/${orderId}/invoice.pdf`, {
    responseType: 'blob',
  });
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `bon-de-livraison-${orderId}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

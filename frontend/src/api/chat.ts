import client from './client';
import type { Conversation, ConversationDetail, Page } from '../types';

export interface CreatedOrderInfo {
  id: string;
  total: number;
  items: number;
}

export interface ProductCardData {
  id: string;
  name: string;
  price: number;
  image_url: string | null;
}

export async function sendMessage(payload: {
  conversation_id?: string;
  customer_name?: string;
  customer_phone?: string;
  customer_address?: string;
  language?: string;
  message: string;
}): Promise<{
  conversation_id: string;
  reply: string;
  language: string;
  order?: CreatedOrderInfo;
  suggested_products?: ProductCardData[];
}> {
  const { data } = await client.post('/api/chat', payload);
  return data;
}

export async function listConversations(params?: {
  page?: number;
  page_size?: number;
}): Promise<Page<Conversation>> {
  const { data } = await client.get('/api/chat/conversations', { params });
  return data;
}

export async function getConversationDetail(
  id: string,
): Promise<ConversationDetail> {
  const { data } = await client.get(`/api/chat/conversations/${id}`);
  return data;
}

export async function updateConversation(
  id: string,
  payload: {
    customer_name?: string;
    customer_phone?: string;
    customer_address?: string;
  },
): Promise<Conversation> {
  const { data } = await client.patch(`/api/chat/conversations/${id}`, payload);
  return data;
}

export async function closeConversation(id: string): Promise<Conversation> {
  const { data } = await client.patch(`/api/chat/conversations/${id}/close`);
  return data;
}

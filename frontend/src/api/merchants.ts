import client from './client';
import type { Merchant, Store, StoreMember, Page, StoreCreatePayload, StoreUpdatePayload } from '../types';

export async function getMerchant(): Promise<Merchant> {
  const { data } = await client.get('/api/merchants/me');
  return data;
}

export async function createMerchant(payload: {
  company_name: string;
  verification_status?: 'pending' | 'verified' | 'rejected';
}): Promise<Merchant> {
  const { data } = await client.post('/api/merchants', payload);
  return data;
}

export async function updateMerchant(payload: {
  company_name?: string;
  verification_status?: 'pending' | 'verified' | 'rejected';
}): Promise<Merchant> {
  const { data } = await client.put('/api/merchants/me', payload);
  return data;
}

export async function listStores(params?: { page?: number; page_size?: number }): Promise<Page<Store>> {
  const { data } = await client.get('/api/stores', { params });
  return data;
}

export async function createStore(payload: StoreCreatePayload): Promise<Store> {
  const { data } = await client.post('/api/stores', payload);
  return data;
}

export async function updateStore(id: string, payload: StoreUpdatePayload): Promise<Store> {
  const { data } = await client.put(`/api/stores/${id}`, payload);
  return data;
}

export async function deleteStore(id: string): Promise<void> {
  await client.delete(`/api/stores/${id}`);
}

export async function listStoreMembers(storeId: string, params?: { page?: number; page_size?: number }): Promise<Page<StoreMember>> {
  const { data } = await client.get(`/api/stores/${storeId}/members`, { params });
  return data;
}
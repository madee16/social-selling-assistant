import client from './client';
import type { Buyer, BuyerPayload, ConsentRecord, ConsentRecordPayload, Page } from '../types';

export async function listBuyers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<Page<Buyer>> {
  const { data } = await client.get('/api/buyers', { params });
  return data;
}

export async function getBuyer(id: string): Promise<Buyer> {
  const { data } = await client.get(`/api/buyers/${id}`);
  return data;
}

export async function createBuyer(payload: BuyerPayload): Promise<Buyer> {
  const { data } = await client.post('/api/buyers', payload);
  return data;
}

export async function updateBuyer(id: string, payload: BuyerPayload): Promise<Buyer> {
  const { data } = await client.put(`/api/buyers/${id}`, payload);
  return data;
}

export async function deleteBuyer(id: string): Promise<void> {
  await client.delete(`/api/buyers/${id}`);
}

export async function listConsentRecords(buyerId: string, params?: { page?: number; page_size?: number }): Promise<Page<ConsentRecord>> {
  const { data } = await client.get(`/api/buyers/${buyerId}/consent-records`, { params });
  return data;
}

export async function createConsentRecord(payload: ConsentRecordPayload): Promise<ConsentRecord> {
  const { data } = await client.post('/api/consent-records', payload);
  return data;
}

export async function updateConsentRecord(id: string, payload: { granted?: boolean; consent_text?: string; meta_data?: Record<string, unknown> }): Promise<ConsentRecord> {
  const { data } = await client.put(`/api/consent-records/${id}`, payload);
  return data;
}
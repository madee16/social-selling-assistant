import client from './client';
import type { Collection, CollectionPayload, Page } from '../types';

export async function listCollections(params?: { page?: number; page_size?: number }): Promise<Page<Collection>> {
  const { data } = await client.get('/api/collections', { params });
  return data;
}

export async function getCollection(id: string): Promise<Collection> {
  const { data } = await client.get(`/api/collections/${id}`);
  return data;
}

export async function createCollection(payload: CollectionPayload): Promise<Collection> {
  const { data } = await client.post('/api/collections', payload);
  return data;
}

export async function updateCollection(id: string, payload: CollectionPayload): Promise<Collection> {
  const { data } = await client.put(`/api/collections/${id}`, payload);
  return data;
}

export async function deleteCollection(id: string): Promise<void> {
  await client.delete(`/api/collections/${id}`);
}
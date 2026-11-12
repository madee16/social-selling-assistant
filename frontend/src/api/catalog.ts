import client from './client';
import type {
  AttributeDef,
  AttributeDefPayload,
  InventoryPayload,
  InventoryRecord,
  Page,
  Price,
  PricePayload,
  ProductVariant,
  ProductVariantPayload,
} from '../types';

// Attribute definitions
export async function listAttributeDefs(params?: { page?: number; page_size?: number }): Promise<Page<AttributeDef>> {
  const { data } = await client.get('/api/attribute-defs', { params });
  return data;
}

export async function createAttributeDef(payload: AttributeDefPayload): Promise<AttributeDef> {
  const { data } = await client.post('/api/attribute-defs', payload);
  return data;
}

export async function updateAttributeDef(id: string, payload: AttributeDefPayload): Promise<AttributeDef> {
  const { data } = await client.put(`/api/attribute-defs/${id}`, payload);
  return data;
}

export async function deleteAttributeDef(id: string): Promise<void> {
  await client.delete(`/api/attribute-defs/${id}`);
}

// Variants
export async function listVariants(productId: string, params?: { page?: number; page_size?: number }): Promise<Page<ProductVariant>> {
  const { data } = await client.get(`/api/products/${productId}/variants`, { params });
  return data;
}

export async function createVariant(productId: string, payload: ProductVariantPayload): Promise<ProductVariant> {
  const { data } = await client.post(`/api/products/${productId}/variants`, payload);
  return data;
}

export async function updateVariant(id: string, payload: ProductVariantPayload): Promise<ProductVariant> {
  const { data } = await client.put(`/api/variants/${id}`, payload);
  return data;
}

export async function deleteVariant(id: string): Promise<void> {
  await client.delete(`/api/variants/${id}`);
}

// Inventory
export async function listInventory(productId: string, params?: { page?: number; page_size?: number }): Promise<Page<InventoryRecord>> {
  const { data } = await client.get(`/api/products/${productId}/inventory`, { params });
  return data;
}

export async function createInventory(productId: string, payload: InventoryPayload): Promise<InventoryRecord> {
  const { data } = await client.post(`/api/products/${productId}/inventory`, payload);
  return data;
}

export async function updateInventory(id: string, payload: Partial<InventoryPayload>): Promise<InventoryRecord> {
  const { data } = await client.put(`/api/inventory/${id}`, payload);
  return data;
}

export async function deleteInventory(id: string): Promise<void> {
  await client.delete(`/api/inventory/${id}`);
}

// Prices
export async function listPrices(productId: string, params?: { page?: number; page_size?: number }): Promise<Page<Price>> {
  const { data } = await client.get(`/api/products/${productId}/prices`, { params });
  return data;
}

export async function createPrice(productId: string, payload: PricePayload): Promise<Price> {
  const { data } = await client.post(`/api/products/${productId}/prices`, payload);
  return data;
}

export async function updatePrice(id: string, payload: Partial<PricePayload>): Promise<Price> {
  const { data } = await client.put(`/api/prices/${id}`, payload);
  return data;
}

export async function deletePrice(id: string): Promise<void> {
  await client.delete(`/api/prices/${id}`);
}
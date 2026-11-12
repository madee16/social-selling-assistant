import client from './client';
import type { Category, Product, Page } from '../types';

export async function listCategories(page = 1): Promise<Page<Category>> {
  const { data } = await client.get('/api/categories', { params: { page } });
  return data;
}

export async function createCategory(name: string, description?: string): Promise<Category> {
  const { data } = await client.post('/api/categories', { name, description });
  return data;
}

export async function updateCategory(id: string, payload: Partial<Category>): Promise<Category> {
  const { data } = await client.put(`/api/categories/${id}`, payload);
  return data;
}

export async function deleteCategory(id: string): Promise<void> {
  await client.delete(`/api/categories/${id}`);
}

export async function listProducts(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  category_id?: string;
  active_only?: boolean;
}): Promise<Page<Product>> {
  const { data } = await client.get('/api/products', { params });
  return data;
}

export async function getProduct(id: string): Promise<Product> {
  const { data } = await client.get(`/api/products/${id}`);
  return data;
}

export async function createProduct(payload: {
  name: string;
  price: number;
  description?: string;
  category_id?: string;
  image_url?: string;
  stock_quantity?: number;
}): Promise<Product> {
  const { data } = await client.post('/api/products', payload);
  return data;
}

export async function updateProduct(id: string, payload: Partial<Product>): Promise<Product> {
  const { data } = await client.put(`/api/products/${id}`, payload);
  return data;
}

export async function deleteProduct(id: string): Promise<void> {
  await client.delete(`/api/products/${id}`);
}

export async function importProducts(file: File, categoryId?: string): Promise<{ imported: number; errors: string[] }> {
  const form = new FormData();
  form.append('file', file);
  if (categoryId) form.append('category_id', categoryId);
  const { data } = await client.post('/api/import/products', form);
  return data;
}

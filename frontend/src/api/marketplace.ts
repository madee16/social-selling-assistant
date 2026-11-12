import client from './client';
import type {
  MarketplaceListing,
  MarketplaceListingPayload,
  Page,
  ProductScore,
  ProductScorePayload,
  SellerTrustPayload,
  SellerTrustScore,
  SeoData,
  SeoDataPayload,
  SeoGenerateResponse,
  SeoScore,
} from '../types';

// SEO
export async function listSeoData(params?: { page?: number; page_size?: number; entity_type?: string }): Promise<Page<SeoData>> {
  const { data } = await client.get('/api/seo', { params });
  return data;
}

export async function createSeoData(payload: SeoDataPayload): Promise<SeoData> {
  const { data } = await client.post('/api/seo', payload);
  return data;
}

export async function updateSeoData(id: string, payload: Partial<SeoDataPayload>): Promise<SeoData> {
  const { data } = await client.put(`/api/seo/${id}`, payload);
  return data;
}

export async function deleteSeoData(id: string): Promise<void> {
  await client.delete(`/api/seo/${id}`);
}

export async function listSeoScores(seoId: string, params?: { page?: number; page_size?: number }): Promise<Page<SeoScore>> {
  const { data } = await client.get(`/api/seo/${seoId}/scores`, { params });
  return data;
}

export async function generateAiSeo(entityType: string, entityId: string): Promise<SeoGenerateResponse> {
  const { data } = await client.post(`/api/seo/${entityType}/${entityId}/generate`);
  return data;
}

export function getShareUrl(entityType: string, slugOrId: string): string {
  const origin = window.location.origin;
  return `${origin}/share/${entityType}/${slugOrId}`;
}


// Marketplace listings
export async function listMarketplaceListings(productId: string, params?: { page?: number; page_size?: number }): Promise<Page<MarketplaceListing>> {
  const { data } = await client.get(`/api/products/${productId}/listings`, { params });
  return data;
}

export async function createMarketplaceListing(productId: string, payload: MarketplaceListingPayload): Promise<MarketplaceListing> {
  const { data } = await client.post(`/api/products/${productId}/listings`, payload);
  return data;
}

export async function updateMarketplaceListing(id: string, payload: Partial<MarketplaceListingPayload>): Promise<MarketplaceListing> {
  const { data } = await client.put(`/api/marketplace-listings/${id}`, payload);
  return data;
}

export async function deleteMarketplaceListing(id: string): Promise<void> {
  await client.delete(`/api/marketplace-listings/${id}`);
}

// Product scores
export async function listProductScores(productId: string, params?: { page?: number; page_size?: number }): Promise<Page<ProductScore>> {
  const { data } = await client.get(`/api/products/${productId}/scores`, { params });
  return data;
}

export async function createProductScore(productId: string, payload: ProductScorePayload): Promise<ProductScore> {
  const { data } = await client.post(`/api/products/${productId}/scores`, payload);
  return data;
}

export async function updateProductScore(id: string, payload: Partial<ProductScorePayload>): Promise<ProductScore> {
  const { data } = await client.put(`/api/product-scores/${id}`, payload);
  return data;
}

export async function deleteProductScore(id: string): Promise<void> {
  await client.delete(`/api/product-scores/${id}`);
}

// Seller trust
export async function listSellerTrust(params?: { page?: number; page_size?: number }): Promise<Page<SellerTrustScore>> {
  const { data } = await client.get('/api/seller-trust', { params });
  return data;
}

export async function createSellerTrust(payload: SellerTrustPayload): Promise<SellerTrustScore> {
  const { data } = await client.post('/api/seller-trust', payload);
  return data;
}

export async function updateSellerTrust(id: string, payload: Partial<SellerTrustPayload>): Promise<SellerTrustScore> {
  const { data } = await client.put(`/api/seller-trust/${id}`, payload);
  return data;
}

export async function deleteSellerTrust(id: string): Promise<void> {
  await client.delete(`/api/seller-trust/${id}`);
}
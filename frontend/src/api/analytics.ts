import client from './client';
import type { AnalyticsResponse, DateRangeParams } from '../types';

export async function getAnalytics(params?: DateRangeParams): Promise<AnalyticsResponse> {
  const { data } = await client.get('/api/analytics', { params });
  return data;
}
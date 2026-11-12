import client from './client';
import type { WidgetSettings } from '../types';

export async function getWidgetSettings(): Promise<WidgetSettings> {
  const { data } = await client.get('/api/widget/settings');
  return data;
}

export async function updateWidgetSettings(payload: Partial<WidgetSettings>): Promise<WidgetSettings> {
  const { data } = await client.put('/api/widget/settings', payload);
  return data;
}

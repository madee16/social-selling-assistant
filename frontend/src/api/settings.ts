import client from './client';
import type { User } from '../types';

export async function getSettings(): Promise<User> {
  const { data } = await client.get('/api/settings');
  return data;
}

export async function updateProfile(payload: {
  company_name?: string;
  phone?: string | null;
  company_logo_url?: string | null;
}): Promise<User> {
  const { data } = await client.put('/api/settings/profile', payload);
  return data;
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<{ detail: string }> {
  const { data } = await client.put('/api/settings/password', payload);
  return data;
}

export async function updatePreferences(payload: {
  preferred_language?: string;
  currency?: string;
  notifications_enabled?: boolean;
  ai_custom_instructions?: string | null;
}): Promise<User> {
  const { data } = await client.put('/api/settings/preferences', payload);
  return data;
}

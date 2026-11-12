import client from './client';
import type { AuthResponse, User } from '../types';

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await client.post('/api/auth/login', { email, password });
  return data;
}

export async function register(
  email: string,
  password: string,
  company_name: string,
  phone?: string,
): Promise<AuthResponse> {
  const { data } = await client.post('/api/auth/register', {
    email,
    password,
    company_name,
    phone,
  });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await client.get('/api/auth/me');
  return data;
}

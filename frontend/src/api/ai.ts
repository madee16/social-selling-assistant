import client from './client';
import type { AIMessage, AISession, AISessionPayload, AIToolCall, Page } from '../types';

export async function listSessions(params?: { page?: number; page_size?: number; status?: string }): Promise<Page<AISession>> {
  const { data } = await client.get('/api/ai/sessions', { params });
  return data;
}

export async function getSession(id: string): Promise<AISession> {
  const { data } = await client.get(`/api/ai/sessions/${id}`);
  return data;
}

export async function createSession(payload: AISessionPayload): Promise<AISession> {
  const { data } = await client.post('/api/ai/sessions', payload);
  return data;
}

export async function updateSession(id: string, payload: Partial<AISessionPayload>): Promise<AISession> {
  const { data } = await client.put(`/api/ai/sessions/${id}`, payload);
  return data;
}

export async function deleteSession(id: string): Promise<void> {
  await client.delete(`/api/ai/sessions/${id}`);
}

export async function listMessages(sessionId: string, params?: { page?: number; page_size?: number }): Promise<Page<AIMessage>> {
  const { data } = await client.get(`/api/ai/sessions/${sessionId}/messages`, { params });
  return data;
}

export async function listToolCalls(sessionId: string, params?: { page?: number; page_size?: number }): Promise<Page<AIToolCall>> {
  const { data } = await client.get(`/api/ai/sessions/${sessionId}/tool-calls`, { params });
  return data;
}
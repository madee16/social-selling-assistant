import client from './client';

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string | null;
  link: string | null;
  read: boolean;
  created_at: string;
}

export async function listNotifications(unreadOnly = false): Promise<{ items: NotificationItem[] }> {
  const { data } = await client.get('/api/notifications', { params: { unread_only: unreadOnly } });
  return data;
}

export async function getUnreadCount(): Promise<{ count: number }> {
  const { data } = await client.get('/api/notifications/unread-count');
  return data;
}

export async function markRead(id: string): Promise<void> {
  await client.put(`/api/notifications/${id}/read`);
}

export async function markAllRead(): Promise<void> {
  await client.put('/api/notifications/read-all');
}

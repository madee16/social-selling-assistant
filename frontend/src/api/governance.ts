import client from './client';
import type {
  Approval,
  ApprovalPayload,
  AuditLog,
  AutomationRule,
  AutomationRulePayload,
  EventPayload,
  EventRecord,
  Page,
} from '../types';

// Approvals
export async function listApprovals(params?: { page?: number; page_size?: number; status?: string }): Promise<Page<Approval>> {
  const { data } = await client.get('/api/approvals', { params });
  return data;
}

export async function createApproval(payload: ApprovalPayload): Promise<Approval> {
  const { data } = await client.post('/api/approvals', payload);
  return data;
}

export async function updateApproval(id: string, payload: { status?: string; rejection_reason?: string; approver_id?: string }): Promise<Approval> {
  const { data } = await client.put(`/api/approvals/${id}`, payload);
  return data;
}

// Automation rules
export async function listAutomationRules(params?: { page?: number; page_size?: number; active_only?: boolean }): Promise<Page<AutomationRule>> {
  const { data } = await client.get('/api/automation-rules', { params });
  return data;
}

export async function createAutomationRule(payload: AutomationRulePayload): Promise<AutomationRule> {
  const { data } = await client.post('/api/automation-rules', payload);
  return data;
}

export async function updateAutomationRule(id: string, payload: Partial<AutomationRulePayload>): Promise<AutomationRule> {
  const { data } = await client.put(`/api/automation-rules/${id}`, payload);
  return data;
}

export async function deleteAutomationRule(id: string): Promise<void> {
  await client.delete(`/api/automation-rules/${id}`);
}

// Audit logs
export async function listAuditLogs(params?: { page?: number; page_size?: number }): Promise<Page<AuditLog>> {
  const { data } = await client.get('/api/audit-logs', { params });
  return data;
}

// Events
export async function listEvents(params?: { page?: number; page_size?: number; event_type?: string }): Promise<Page<EventRecord>> {
  const { data } = await client.get('/api/events', { params });
  return data;
}

export async function createEvent(payload: EventPayload): Promise<EventRecord> {
  const { data } = await client.post('/api/events', payload);
  return data;
}

export async function deleteEvent(id: string): Promise<void> {
  await client.delete(`/api/events/${id}`);
}
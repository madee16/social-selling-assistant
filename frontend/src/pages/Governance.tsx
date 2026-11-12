import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  listApprovals, updateApproval, createApproval,
  listAutomationRules, createAutomationRule, updateAutomationRule, deleteAutomationRule,
  listAuditLogs, listEvents, createEvent, deleteEvent,
} from '../api/governance';
import type { Approval, AuditLog, AutomationRule, EventPayload, EventRecord, Page } from '../types';
import { useToast } from '../contexts/ToastContext';
import { Button, Card, Input, Modal, ConfirmDialog, Badge } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

type Tab = 'approvals' | 'rules' | 'audit' | 'events';

const statusVariant = (s: string): 'success' | 'danger' | 'warning' | 'default' | 'info' =>
  s === 'approved' ? 'success' : s === 'rejected' || s === 'failed' ? 'danger' : s === 'pending' || s === 'draft' ? 'warning' : 'info';

export default function Governance() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [tab, setTab] = useState<Tab>('approvals');

  // approvals
  const [approvals, setApprovals] = useState<Page<Approval> | null>(null);
  const [approvalsLoading, setApprovalsLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<Approval | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalForm, setApprovalForm] = useState({ approval_type: '', entity_type: 'product', entity_id: '', title: '', description: '' });

  // rules
  const [rules, setRules] = useState<Page<AutomationRule> | null>(null);
  const [rulesLoading, setRulesLoading] = useState(true);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [ruleEditId, setRuleEditId] = useState<string | null>(null);
  const [ruleForm, setRuleForm] = useState({ name: '', event_type: '', description: '', conditions: '', actions: '', is_active: true, priority: '0' });
  const [ruleConfirmDelete, setRuleConfirmDelete] = useState<AutomationRule | null>(null);

  // audit
  const [logs, setLogs] = useState<Page<AuditLog> | null>(null);
  const [logsLoading, setLogsLoading] = useState(true);

  // events
  const [events, setEvents] = useState<Page<EventRecord> | null>(null);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [eventModalOpen, setEventModalOpen] = useState(false);
  const [eventForm, setEventForm] = useState({ event_type: 'custom', entity_type: '', entity_id: '', payload: '' });
  const [eventConfirmDelete, setEventConfirmDelete] = useState<EventRecord | null>(null);

  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const errMsg = (err: unknown) => (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error');

  const loadApprovals = useCallback(async () => {
    setApprovalsLoading(true);
    try { setApprovals(await listApprovals({ page_size: 100 })); } finally { setApprovalsLoading(false); }
  }, []);

  const loadRules = useCallback(async () => {
    setRulesLoading(true);
    try { setRules(await listAutomationRules({ page_size: 100 })); } finally { setRulesLoading(false); }
  }, []);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try { setLogs(await listAuditLogs({ page_size: 100 })); } finally { setLogsLoading(false); }
  }, []);

  const loadEvents = useCallback(async () => {
    setEventsLoading(true);
    try { setEvents(await listEvents({ page_size: 100 })); } finally { setEventsLoading(false); }
  }, []);

  useEffect(() => {
    if (tab === 'approvals') loadApprovals();
    if (tab === 'rules') loadRules();
    if (tab === 'audit') loadLogs();
    if (tab === 'events') loadEvents();
  }, [tab, loadApprovals, loadRules, loadLogs, loadEvents]);

  // ---- approvals ----
  const setApprovalStatus = async (a: Approval, status: string, rejection_reason?: string) => {
    setBusyId(a.id);
    try {
      await updateApproval(a.id, { status, rejection_reason });
      showToast('success', status === 'approved' ? t('gov.approved') : status === 'rejected' ? t('gov.rejected') : t('gov.updated'));
      await loadApprovals();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setBusyId(null); }
  };

  const saveApproval = async () => {
    setSaving(true);
    try {
      await createApproval({
        approval_type: approvalForm.approval_type.trim(),
        entity_type: approvalForm.entity_type,
        entity_id: approvalForm.entity_id.trim(),
        title: approvalForm.title.trim() || undefined,
        description: approvalForm.description.trim() || undefined,
      });
      setApprovalModalOpen(false);
      setApprovalForm({ approval_type: '', entity_type: 'product', entity_id: '', title: '', description: '' });
      await loadApprovals();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  // ---- rules ----
  const openRuleCreate = () => {
    setRuleForm({ name: '', event_type: '', description: '', conditions: '', actions: '', is_active: true, priority: '0' });
    setRuleEditId(null);
    setRuleModalOpen(true);
  };

  const openRuleEdit = (r: AutomationRule) => {
    setRuleForm({
      name: r.name,
      event_type: r.event_type,
      description: r.description || '',
      conditions: r.conditions ? JSON.stringify(r.conditions) : '',
      actions: r.actions ? JSON.stringify(r.actions) : '',
      is_active: r.is_active,
      priority: String(r.priority),
    });
    setRuleEditId(r.id);
    setRuleModalOpen(true);
  };

  const saveRule = async () => {
    setSaving(true);
    try {
      let conditions: Record<string, unknown> | undefined;
      let actions: Record<string, unknown> | undefined;
      if (ruleForm.conditions.trim()) {
        try { conditions = JSON.parse(ruleForm.conditions); } catch { showToast('error', t('catalog.invalid_json')); return; }
      }
      if (ruleForm.actions.trim()) {
        try { actions = JSON.parse(ruleForm.actions); } catch { showToast('error', t('catalog.invalid_json')); return; }
      }
      const payload = {
        name: ruleForm.name.trim(),
        event_type: ruleForm.event_type.trim(),
        description: ruleForm.description.trim() || undefined,
        conditions,
        actions,
        is_active: ruleForm.is_active,
        priority: parseInt(ruleForm.priority) || 0,
      };
      if (ruleEditId) {
        await updateAutomationRule(ruleEditId, payload);
        showToast('success', t('gov.rule_updated'));
      } else {
        await createAutomationRule(payload);
        showToast('success', t('gov.rule_created'));
      }
      setRuleModalOpen(false);
      await loadRules();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const toggleRule = async (r: AutomationRule) => {
    setBusyId(r.id);
    try {
      await updateAutomationRule(r.id, { is_active: !r.is_active });
      await loadRules();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setBusyId(null); }
  };

  const removeRule = async () => {
    if (!ruleConfirmDelete) return;
    try {
      await deleteAutomationRule(ruleConfirmDelete.id);
      showToast('success', t('gov.rule_deleted'));
      await loadRules();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setRuleConfirmDelete(null); }
  };

  // ---- events ----
  const saveEvent = async () => {
    setSaving(true);
    try {
      let payload: Record<string, unknown> | undefined;
      if (eventForm.payload.trim()) {
        try { payload = JSON.parse(eventForm.payload); } catch { showToast('error', t('catalog.invalid_json')); return; }
      }
      await createEvent({
        event_type: eventForm.event_type as EventPayload['event_type'],
        entity_type: eventForm.entity_type.trim() || undefined,
        entity_id: eventForm.entity_id.trim() || undefined,
        payload,
      });
      setEventModalOpen(false);
      setEventForm({ event_type: 'custom', entity_type: '', entity_id: '', payload: '' });
      await loadEvents();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const removeEvent = async () => {
    if (!eventConfirmDelete) return;
    try {
      await deleteEvent(eventConfirmDelete.id);
      showToast('success', t('gov.event_deleted'));
      await loadEvents();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setEventConfirmDelete(null); }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'approvals', label: t('gov.tab_approvals') },
    { key: 'rules', label: t('gov.tab_rules') },
    { key: 'audit', label: t('gov.tab_audit') },
    { key: 'events', label: t('gov.tab_events') },
  ];

  const loadingMap = { approvals: approvalsLoading, rules: rulesLoading, audit: logsLoading, events: eventsLoading }[tab];
  const emptyMap: Record<Tab, string> = { approvals: 'gov.no_approvals', rules: 'gov.no_rules', audit: 'gov.no_logs', events: 'gov.no_events' };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('gov.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('gov.subtitle')}</p>
        </div>
        {tab === 'approvals' && <Button onClick={() => { setApprovalForm({ approval_type: '', entity_type: 'product', entity_id: '', title: '', description: '' }); setApprovalModalOpen(true); }}>{t('gov.add_approval')}</Button>}
        {tab === 'rules' && <Button onClick={openRuleCreate}>{t('gov.add_rule')}</Button>}
        {tab === 'events' && <Button onClick={() => { setEventForm({ event_type: 'custom', entity_type: '', entity_id: '', payload: '' }); setEventModalOpen(true); }}>{t('gov.add_event')}</Button>}
      </div>

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        {tabs.map((tb) => (
          <button key={tb.key} onClick={() => setTab(tb.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === tb.key ? 'border-blue-600 text-blue-600 dark:text-blue-400 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}>
            {tb.label}
          </button>
        ))}
      </div>

      {loadingMap ? <SkeletonTable rows={5} cols={5} /> : null}

      {!loadingMap && (
        <>
          {tab === 'approvals' && (!approvals || approvals.items.length === 0 ? (
            <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t(emptyMap.approvals)}</p></Card>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.type')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.title')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.entity')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.status')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.date')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {approvals.items.map((a) => (
                    <tr key={a.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3"><Badge variant="cobalt">{a.approval_type}</Badge></td>
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{a.title || '—'}</p>
                        {a.rejection_reason && <p className="text-xs text-rose-500 mt-0.5">✕ {a.rejection_reason}</p>}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{a.entity_type} · {a.entity_id.slice(0, 8)}</td>
                      <td className="px-4 py-3"><Badge variant={statusVariant(a.status)}>{a.status}</Badge></td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{new Date(a.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-right">
                        {a.status === 'pending' && (
                          <span className="inline-flex gap-2">
                            <Button size="sm" variant="success" loading={busyId === a.id} onClick={() => setApprovalStatus(a, 'approved')}>{t('gov.approve')}</Button>
                            <Button size="sm" variant="danger" disabled={busyId === a.id} onClick={() => { setRejectTarget(a); setRejectReason(''); }}>{t('gov.reject')}</Button>
                          </span>
                        )}
                        {a.status !== 'pending' && <span className="text-xs text-slate-400 dark:text-slate-500">{t('gov.decided')}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

          {tab === 'rules' && (!rules || rules.items.length === 0 ? (
            <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t(emptyMap.rules)}</p></Card>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.name')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.event_type')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.priority')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.executions')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.status')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {rules.items.map((r) => (
                    <tr key={r.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{r.name}</p>
                        {r.description && <p className="text-xs text-slate-400 dark:text-slate-500 truncate max-w-[220px]">{r.description}</p>}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{r.event_type}</td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{r.priority}</td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{r.execution_count}</td>
                      <td className="px-4 py-3">
                        <Button size="sm" variant={r.is_active ? 'success' : 'secondary'} loading={busyId === r.id} onClick={() => toggleRule(r)}>
                          {r.is_active ? t('gov.active') : t('gov.inactive')}
                        </Button>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => openRuleEdit(r)} className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium mr-3">{t('common.edit')}</button>
                        <button onClick={() => setRuleConfirmDelete(r)} className="text-sm text-rose-600 hover:text-rose-700 dark:text-rose-400 font-medium">{t('common.delete')}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

          {tab === 'audit' && (!logs || logs.items.length === 0 ? (
            <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t(emptyMap.audit)}</p></Card>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.action')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.entity')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.ip')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.date')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {logs.items.map((l) => (
                      <tr key={l.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                        <td className="px-4 py-3">
                          <Badge variant="cobalt">{l.action}</Badge>
                          {l.details && <span className="ml-2 text-xs text-slate-400 dark:text-slate-500 font-mono">{JSON.stringify(l.details)}</span>}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{l.entity_type ? `${l.entity_type} ${l.entity_id ? '· ' + l.entity_id.slice(0, 8) : ''}` : '—'}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{l.ip_address || '—'}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{new Date(l.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          {tab === 'events' && (!events || events.items.length === 0 ? (
            <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t(emptyMap.events)}</p></Card>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.event_type')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.entity')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.payload')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.date')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('gov.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {events.items.map((e) => (
                    <tr key={e.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                      <td className="px-4 py-3"><Badge variant="coral">{e.event_type}</Badge></td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{e.entity_type ? `${e.entity_type} · ${(e.entity_id || '').slice(0, 8)}` : '—'}</td>
                      <td className="px-4 py-3 text-xs text-slate-500 max-w-[220px] truncate dark:text-slate-400 font-mono">{e.payload ? JSON.stringify(e.payload) : '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{new Date(e.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => setEventConfirmDelete(e)} className="text-sm text-rose-600 hover:text-rose-700 dark:text-rose-400 font-medium">{t('common.delete')}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </>
      )}

      {/* Approve/reject */}
      <Modal open={!!rejectTarget} onClose={() => setRejectTarget(null)} title={t('gov.reject_approval')}>
        <div className="space-y-4">
          <Input label={t('gov.rejection_reason')} value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setRejectTarget(null)}>{t('common.cancel')}</Button>
            <Button variant="danger" onClick={() => { if (rejectTarget) setApprovalStatus(rejectTarget, 'rejected', rejectReason || undefined); setRejectTarget(null); }}>
              {t('gov.reject')}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={approvalModalOpen} onClose={() => setApprovalModalOpen(false)} title={t('gov.new_approval')}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={`${t('gov.type')} *`} value={approvalForm.approval_type} onChange={(e) => setApprovalForm({ ...approvalForm, approval_type: e.target.value })} placeholder="price_change" />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('gov.entity')}</label>
              <select value={approvalForm.entity_type} onChange={(e) => setApprovalForm({ ...approvalForm, entity_type: e.target.value })}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
                {['product', 'collection', 'store', 'price', 'listing'].map((ty) => <option key={ty} value={ty}>{ty}</option>)}
              </select>
            </div>
          </div>
          <Input label={`${t('gov.entity_id')} *`} value={approvalForm.entity_id} onChange={(e) => setApprovalForm({ ...approvalForm, entity_id: e.target.value })} />
          <Input label={t('gov.title')} value={approvalForm.title} onChange={(e) => setApprovalForm({ ...approvalForm, title: e.target.value })} />
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('gov.description')}</label>
            <textarea value={approvalForm.description} onChange={(e) => setApprovalForm({ ...approvalForm, description: e.target.value })} rows={3}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setApprovalModalOpen(false)}>{t('common.cancel')}</Button>
            <Button onClick={saveApproval} loading={saving} disabled={!approvalForm.approval_type.trim() || !approvalForm.entity_id.trim()}>{t('common.create')}</Button>
          </div>
        </div>
      </Modal>

      {/* Rules modal */}
      <Modal open={ruleModalOpen} onClose={() => setRuleModalOpen(false)} title={ruleEditId ? t('gov.edit_rule') : t('gov.new_rule')}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={`${t('gov.name')} *`} value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} />
            <Input label={`${t('gov.event_type')} *`} value={ruleForm.event_type} onChange={(e) => setRuleForm({ ...ruleForm, event_type: e.target.value })} placeholder="order_created" />
          </div>
          <Input label={t('gov.description')} value={ruleForm.description} onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })} />
          <div className="grid grid-cols-2 gap-4">
            <Input label={t('gov.conditions')} value={ruleForm.conditions} onChange={(e) => setRuleForm({ ...ruleForm, conditions: e.target.value })} placeholder='{"status": "paid"}' />
            <Input label={t('gov.actions_field')} value={ruleForm.actions} onChange={(e) => setRuleForm({ ...ruleForm, actions: e.target.value })} placeholder='{"notify": true}' />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={t('gov.priority')} type="number" value={ruleForm.priority} onChange={(e) => setRuleForm({ ...ruleForm, priority: e.target.value })} />
            <div className="flex items-end justify-between pb-1">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('gov.active')}</span>
              <button type="button" onClick={() => setRuleForm({ ...ruleForm, is_active: !ruleForm.is_active })}
                className={`relative w-10 h-5 rounded-full transition-colors ${ruleForm.is_active ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all shadow-xs ${ruleForm.is_active ? 'left-5' : 'left-0.5'}`} />
              </button>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setRuleModalOpen(false)}>{t('common.cancel')}</Button>
            <Button onClick={saveRule} loading={saving} disabled={!ruleForm.name.trim() || !ruleForm.event_type.trim()}>{ruleEditId ? t('common.update') : t('common.create')}</Button>
          </div>
        </div>
      </Modal>
      <ConfirmDialog open={!!ruleConfirmDelete} onClose={() => setRuleConfirmDelete(null)} onConfirm={removeRule}
        title={t('gov.delete_rule')} message={t('gov.delete_rule_confirm')} />

      {/* Events modal */}
      <Modal open={eventModalOpen} onClose={() => setEventModalOpen(false)} title={t('gov.new_event')}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('gov.event_type')}</label>
            <select value={eventForm.event_type} onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
              {['holiday', 'season', 'campaign', 'sale', 'custom'].map((ty) => <option key={ty} value={ty}>{ty}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={t('gov.entity')} value={eventForm.entity_type} onChange={(e) => setEventForm({ ...eventForm, entity_type: e.target.value })} placeholder="product" />
            <Input label={t('gov.entity_id')} value={eventForm.entity_id} onChange={(e) => setEventForm({ ...eventForm, entity_id: e.target.value })} placeholder="uuid" />
          </div>
          <Input label={t('gov.payload')} value={eventForm.payload} onChange={(e) => setEventForm({ ...eventForm, payload: e.target.value })} placeholder='{"discount": 20}' />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setEventModalOpen(false)}>{t('common.cancel')}</Button>
            <Button onClick={saveEvent} loading={saving}>{t('common.create')}</Button>
          </div>
        </div>
      </Modal>
      <ConfirmDialog open={!!eventConfirmDelete} onClose={() => setEventConfirmDelete(null)} onConfirm={removeEvent}
        title={t('gov.delete_event')} message={t('gov.delete_event_confirm')} />
    </div>
  );
}
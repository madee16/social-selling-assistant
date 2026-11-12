import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { listSessions, updateSession } from '../api/ai';
import type { AISession, AISessionPayload, Page } from '../types';
import { useToast } from '../contexts/ToastContext';
import { useStore } from '../contexts/StoreContext';
import { Card, Badge, Button } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

const statusVariant = (s: string): 'success' | 'warning' | 'danger' | 'info' | 'default' =>
  s === 'active' ? 'success' : s === 'escalated' ? 'danger' : s === 'closed' ? 'info' : 'default';

export default function AISessions() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const { activeStore } = useStore();

  const [sessions, setSessions] = useState<Page<AISession> | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const errMsg = (err: unknown) => (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setSessions(await listSessions({ page_size: 100, ...(statusFilter ? { status: statusFilter } : {}) }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setLoading(false); }
  }, [statusFilter, showToast, t]);

  useEffect(() => { load(); }, [load]);

  const setStatus = async (s: AISession, status: AISessionPayload['status']) => {
    setBusyId(s.id);
    try {
      await updateSession(s.id, { status });
      showToast('success', t('ai.saved'));
      await load();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setBusyId(null); }
  };

  const filters = ['', 'active', 'closed', 'escalated'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('ai.title')}</h1>
        <p className="text-sm text-slate-500 mt-1 dark:text-slate-400">{t('ai.subtitle')}</p>
      </div>

      {activeStore && (
        <Card className="border border-blue-100 dark:border-blue-900/40 bg-blue-50/40 dark:bg-blue-950/20">
          <div className="flex items-start gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse mt-1 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{activeStore.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t('stores.sessions_scoped', { store: activeStore.name })}</p>
            </div>
          </div>
        </Card>
      )}

      <div className="flex gap-2">
        {filters.map((f) => (
          <button key={f} onClick={() => setStatusFilter(f)}
            className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === f ? 'bg-blue-600 text-white shadow-xs' : 'bg-white text-slate-600 border border-slate-200/90 hover:border-slate-300 dark:bg-slate-900 dark:text-slate-400 dark:border-slate-800 dark:hover:border-slate-700'}`}>
            {f === '' ? t('ai.all') : t(`ai.status_${f}`)}
          </button>
        ))}
      </div>

      {loading ? <SkeletonTable rows={5} cols={5} /> : null}

      {!loading && (!sessions || sessions.items.length === 0 ? (
        <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('ai.no_sessions')}</p></Card>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.intent')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.store')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.buyer')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.messages')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.status')}</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.updated')}</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('ai.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {sessions.items.map((s) => (
                <tr key={s.id} className="hover:bg-blue-50/30 transition-colors cursor-pointer dark:hover:bg-slate-800/40" onClick={() => navigate(`/ai-sessions/${s.id}`)}>
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{s.intent || '—'}</p>
                    {s.conversation_summary && <p className="text-xs text-slate-500 truncate max-w-[240px] dark:text-slate-400">{s.conversation_summary}</p>}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-slate-500 dark:text-slate-400">{s.store_id ? s.store_id.slice(0, 8) : '—'}</td>
                  <td className="px-4 py-3 text-xs font-mono text-slate-500 dark:text-slate-400">{s.buyer_id ? s.buyer_id.slice(0, 8) : '—'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{s.total_messages}</td>
                  <td className="px-4 py-3"><Badge variant={statusVariant(s.status)}>{s.status}</Badge></td>
                  <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{new Date(s.updated_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                    {s.status === 'active' ? (
                      <span className="inline-flex gap-2">
                        <Button size="sm" variant="coral" loading={busyId === s.id} onClick={() => setStatus(s, 'escalated')}>{t('ai.escalate')}</Button>
                        <Button size="sm" variant="secondary" disabled={busyId === s.id} onClick={() => setStatus(s, 'closed')}>{t('ai.close')}</Button>
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400 dark:text-slate-500">{t('ai.closed_status')}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
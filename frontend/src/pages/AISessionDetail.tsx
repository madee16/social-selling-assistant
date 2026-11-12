import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { getSession, listMessages, listToolCalls, updateSession } from '../api/ai';
import type { AIMessage, AISession, AISessionPayload, AIToolCall, Page } from '../types';
import { useToast } from '../contexts/ToastContext';
import { Card, Badge, Button } from '../components/ui';
import Skeleton from '../components/ui/Skeleton';

const roleVariant = (r: string): 'success' | 'info' | 'warning' | 'indigo' | 'default' =>
  r === 'user' ? 'info' : r === 'assistant' ? 'success' : r === 'tool' ? 'warning' : r === 'system' ? 'indigo' : 'default';

const statusVariant = (s: string): 'success' | 'danger' | 'warning' | 'info' | 'default' =>
  s === 'active' ? 'success' : s === 'escalated' ? 'danger' : s === 'closed' ? 'info' : s === 'failed' ? 'danger' : 'default';

const toolVariant = (s: string): 'success' | 'danger' | 'warning' | 'default' =>
  s === 'completed' ? 'success' : s === 'failed' ? 'danger' : s === 'running' ? 'warning' : 'default';

export default function AISessionDetail() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [session, setSession] = useState<AISession | null>(null);
  const [messages, setMessages] = useState<Page<AIMessage> | null>(null);
  const [toolCalls, setToolCalls] = useState<Page<AIToolCall> | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [s, m, tc] = await Promise.all([
        getSession(id),
        listMessages(id, { page_size: 200 }),
        listToolCalls(id, { page_size: 200 }),
      ]);
      setSession(s);
      setMessages(m);
      setToolCalls(tc);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      showToast('error', detail || t('ai.not_found'));
      navigate('/ai-sessions');
    } finally { setLoading(false); }
  }, [id, showToast, t, navigate]);

  useEffect(() => { load(); }, [load]);

  const setStatus = async (status: AISessionPayload['status']) => {
    if (!session) return;
    setBusy(true);
    try {
      const updated = await updateSession(session.id, { status });
      setSession(updated);
      showToast('success', t('ai.saved'));
    } catch (err: unknown) {
      showToast('error', t('common.error'));
    } finally { setBusy(false); }
  };

  if (loading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /><Skeleton className="h-40 w-full" /></div>;
  if (!session) return null;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate('/ai-sessions')} className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium mb-1.5 inline-flex items-center gap-1">← {t('ai.back')}</button>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{session.intent || t('ai.session')}</h1>
          <p className="text-xs font-mono text-slate-500 mt-1 dark:text-slate-400">{session.id}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={statusVariant(session.status)}>{session.status}</Badge>
          {session.status === 'active' && (
            <span className="inline-flex gap-2">
              <Button size="sm" variant="coral" loading={busy} onClick={() => setStatus('escalated')}>{t('ai.escalate')}</Button>
              <Button size="sm" variant="secondary" disabled={busy} onClick={() => setStatus('closed')}>{t('ai.close')}</Button>
            </span>
          )}
        </div>
      </div>

      {session.conversation_summary && (
        <Card>
          <h3 className="text-sm font-semibold text-slate-800 mb-1.5 dark:text-slate-200">{t('ai.summary')}</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">{session.conversation_summary}</p>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Card><p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('ai.store')}</p><p className="text-sm font-medium font-mono text-slate-900 mt-1.5 dark:text-slate-100">{session.store_id ? session.store_id.slice(0, 8) : '—'}</p></Card>
        <Card><p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('ai.buyer')}</p><p className="text-sm font-medium font-mono text-slate-900 mt-1.5 dark:text-slate-100">{session.buyer_id ? session.buyer_id.slice(0, 8) : '—'}</p></Card>
        <Card><p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('ai.messages')}</p><p className="text-base font-semibold text-slate-900 mt-1 dark:text-slate-100">{session.total_messages}</p></Card>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-slate-800 mb-4 dark:text-slate-200">{t('ai.timeline')}</h3>
        {!messages || messages.items.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6 dark:text-slate-500">{t('ai.no_messages')}</p>
        ) : (
          <div className="space-y-4">
            {messages.items.map((m) => (
              <div key={m.id} className="flex gap-3">
                <div className="flex flex-col items-center mt-1">
                  <span className={`w-2.5 h-2.5 rounded-full shrink-0 shadow-xs ${
                    m.role === 'user' ? 'bg-blue-600' : m.role === 'assistant' ? 'bg-emerald-500' : m.role === 'tool' ? 'bg-amber-500' : 'bg-indigo-600'
                  }`} />
                  <span className="w-px bg-slate-200 flex-1 dark:bg-slate-800" />
                </div>
                <div className="flex-1 min-w-0 pb-4">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Badge variant={roleVariant(m.role)}>{m.role}</Badge>
                    <span className="text-xs text-slate-400 dark:text-slate-500">{new Date(m.created_at).toLocaleString()}</span>
                    {m.confidence != null && <span className="text-xs font-medium text-slate-500 dark:text-slate-400">({Math.round(m.confidence * 100)}% conf)</span>}
                  </div>
                  <p className="text-sm text-slate-800 whitespace-pre-wrap dark:text-slate-200">{m.content}</p>
                  {m.tool_calls && (
                    <pre className="mt-2 text-xs bg-slate-900 text-slate-100 border border-slate-800 rounded-lg p-2.5 overflow-x-auto font-mono">{JSON.stringify(m.tool_calls, null, 2)}</pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-slate-800 mb-4 dark:text-slate-200">{t('ai.tool_calls')}</h3>
        {!toolCalls || toolCalls.items.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6 dark:text-slate-500">{t('ai.no_tool_calls')}</p>
        ) : (
          <div className="space-y-3">
            {toolCalls.items.map((tc) => (
              <div key={tc.id} className="border border-slate-200/90 rounded-xl p-3.5 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-800/40">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-slate-900 font-mono dark:text-slate-100">{tc.tool_name}</span>
                  <Badge variant={toolVariant(tc.status)}>{tc.status}</Badge>
                </div>
                {tc.arguments && (
                  <pre className="text-xs text-slate-700 bg-white border border-slate-200/90 rounded-lg p-2.5 mt-2 overflow-x-auto dark:text-slate-300 dark:bg-slate-900 dark:border-slate-800 font-mono">{JSON.stringify(tc.arguments, null, 2)}</pre>
                )}
                {tc.result && (
                  <pre className="text-xs text-slate-600 bg-white border border-slate-200/90 rounded-lg p-2.5 mt-2 overflow-x-auto dark:text-slate-400 dark:bg-slate-900 dark:border-slate-800 font-mono">{JSON.stringify(tc.result, null, 2)}</pre>
                )}
                <p className="text-xs text-slate-400 mt-2 dark:text-slate-500">{new Date(tc.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
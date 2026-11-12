import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listBuyers, createBuyer, updateBuyer, deleteBuyer, listConsentRecords, createConsentRecord, updateConsentRecord } from '../api/buyers';
import type { Buyer, ConsentRecord, Page } from '../types';
import { useToast } from '../contexts/ToastContext';
import { Button, Card, Input, Modal, ConfirmDialog } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

export default function Buyers() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [page, setPage] = useState<Page<Buyer> | null>(null);
  const [search, setSearch] = useState('');
  const [pageNum, setPageNum] = useState(1);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', email: '', phone: '' });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Buyer | null>(null);
  const [detail, setDetail] = useState<Buyer | null>(null);
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [consentsLoading, setConsentsLoading] = useState(false);
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [consentForm, setConsentForm] = useState({ consent_type: '', consent_text: '', granted: true });
  const [consentSaving, setConsentSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listBuyers({ page: pageNum, page_size: 10, search: search || undefined });
      setPage(data);
    } finally { setLoading(false); }
  }, [pageNum, search]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const resetForm = () => {
    setForm({ name: '', email: '', phone: '' });
    setEditId(null);
    setFormOpen(false);
  };

  const openCreate = () => { resetForm(); setFormOpen(true); };

  const openEdit = (b: Buyer) => {
    setForm({ name: b.name || '', email: b.email || '', phone: b.phone || '' });
    setEditId(b.id);
    setFormOpen(true);
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim() || undefined,
        email: form.email.trim() || undefined,
        phone: form.phone.trim() || undefined,
      };
      if (editId) {
        await updateBuyer(editId, payload);
        showToast('success', t('buyers.updated'));
      } else {
        await createBuyer(payload);
        showToast('success', t('buyers.created'));
      }
      resetForm();
      fetchData();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    try {
      await deleteBuyer(confirmDelete.id);
      showToast('success', t('buyers.deleted'));
      fetchData();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally {
      setConfirmDelete(null);
    }
  };

  const openDetail = async (b: Buyer) => {
    setDetail(b);
    setConsentsLoading(true);
    setConsents([]);
    try {
      const res = await listConsentRecords(b.id, { page_size: 50 });
      setConsents(res.items);
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally { setConsentsLoading(false); }
  };

  const handleAddConsent = async () => {
    if (!detail || !consentForm.consent_type.trim()) return;
    setConsentSaving(true);
    try {
      await createConsentRecord({
        buyer_id: detail.id,
        consent_type: consentForm.consent_type.trim(),
        consent_text: consentForm.consent_text.trim() || undefined,
        granted: consentForm.granted,
      });
      setConsentModalOpen(false);
      setConsentForm({ consent_type: '', consent_text: '', granted: true });
      const res = await listConsentRecords(detail.id, { page_size: 50 });
      setConsents(res.items);
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally { setConsentSaving(false); }
  };

  const toggleConsent = async (c: ConsentRecord) => {
    try {
      await updateConsentRecord(c.id, { granted: !c.granted });
      setConsents((prev) => prev.map((x) => (x.id === c.id ? { ...x, granted: !x.granted } : x)));
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('buyers.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('buyers.subtitle')}</p>
        </div>
        <Button onClick={openCreate}>{t('buyers.add')}</Button>
      </div>

      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input placeholder={t('buyers.search')} value={search} onChange={(e) => { setSearch(e.target.value); setPageNum(1); }}
          className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-colors shadow-xs" />
      </div>

      <Modal open={formOpen} onClose={resetForm} title={editId ? t('buyers.edit') : t('buyers.new')}>
        <div className="space-y-4">
          <Input label={t('buyers.name')} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label={t('buyers.email')} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <Input label={t('buyers.phone')} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={resetForm}>{t('common.cancel')}</Button>
            <Button onClick={handleSubmit} loading={saving}>{editId ? t('common.update') : t('common.create')}</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!detail} onClose={() => setDetail(null)} title={detail?.name || detail?.email || t('buyers.detail')}>
        {detail && (
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-bold text-base shadow-sm">
                {(detail.name || detail.email || '?').slice(0, 2).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{detail.name || '—'}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{detail.email || '—'}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{detail.phone || '—'}</p>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{t('buyers.consents')}</h4>
              <Button size="sm" onClick={() => { setConsentForm({ consent_type: '', consent_text: '', granted: true }); setConsentModalOpen(true); }}>
                {t('buyers.add_consent')}
              </Button>
            </div>

            {consentsLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-lg" />)}
              </div>
            ) : consents.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-6">{t('buyers.no_consents')}</p>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800 border border-slate-200/90 dark:border-slate-800 rounded-xl overflow-hidden">
                {consents.map((c) => (
                  <div key={c.id} className="flex items-center justify-between px-4 py-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{c.consent_type}</p>
                      {c.consent_text && <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[260px]">{c.consent_text}</p>}
                      <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{new Date(c.created_at).toLocaleDateString()}</p>
                    </div>
                    <button onClick={() => toggleConsent(c)}
                      className={`shrink-0 text-xs font-semibold px-2.5 py-1.5 rounded-lg border transition-colors ${
                        c.granted ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-800/60 dark:hover:bg-emerald-950/50' : 'bg-rose-50 text-rose-600 border-rose-200 hover:bg-rose-100 dark:bg-rose-950/30 dark:text-rose-400 dark:border-rose-800/60 dark:hover:bg-rose-950/50'
                      }`}>
                      {c.granted ? t('buyers.granted') : t('buyers.denied')}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal open={consentModalOpen} onClose={() => setConsentModalOpen(false)} title={t('buyers.add_consent')}>
        <div className="space-y-4">
          <Input label={t('buyers.consent_type')} value={consentForm.consent_type} onChange={(e) => setConsentForm({ ...consentForm, consent_type: e.target.value })} placeholder="whatsapp_marketing" />
          <Input label={t('buyers.consent_text')} value={consentForm.consent_text} onChange={(e) => setConsentForm({ ...consentForm, consent_text: e.target.value })} />
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('buyers.granted_label')}</label>
            <button onClick={() => setConsentForm({ ...consentForm, granted: !consentForm.granted })}
              className={`relative w-10 h-5 rounded-full transition-colors ${consentForm.granted ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all shadow-xs ${consentForm.granted ? 'left-5' : 'left-0.5'}`} />
            </button>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setConsentModalOpen(false)}>{t('common.cancel')}</Button>
            <Button onClick={handleAddConsent} loading={consentSaving} disabled={!consentForm.consent_type.trim()}>{t('common.create')}</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={!!confirmDelete} onClose={() => setConfirmDelete(null)} onConfirm={handleDelete}
        title={t('buyers.delete')} message={t('buyers.delete_confirm')} />

      {loading ? (
        <SkeletonTable rows={5} cols={5} />
      ) : !page || page.items.length === 0 ? (
        <Card>
          <div className="text-center py-8">
            <svg className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <p className="text-slate-600 dark:text-slate-300 font-medium mt-3">{t('buyers.no_buyers')}</p>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-0.5">{t('buyers.no_buyers_desc')}</p>
          </div>
        </Card>
      ) : (
        <>
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('buyers.name')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('buyers.email')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('buyers.phone')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('buyers.since')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('buyers.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {page.items.map((b) => (
                    <tr key={b.id} className="hover:bg-blue-50/30 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3">
                        <button onClick={() => openDetail(b)} className="flex items-center gap-3 text-left">
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold dark:bg-blue-900/40 dark:text-blue-300">
                            {(b.name || b.email || '?').slice(0, 2).toUpperCase()}
                          </div>
                          <span className="text-sm font-medium text-slate-900 dark:text-slate-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">{b.name || b.email || '—'}</span>
                        </button>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{b.email || '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{b.phone || '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{new Date(b.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => openDetail(b)} className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium mr-3">{t('buyers.view')}</button>
                        <button onClick={() => openEdit(b)} className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium mr-3">{t('common.edit')}</button>
                        <button onClick={() => setConfirmDelete(b)} className="text-sm text-rose-600 hover:text-rose-700 dark:text-rose-400 font-medium">{t('common.delete')}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {page.total_pages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <button disabled={pageNum <= 1} onClick={() => setPageNum(pageNum - 1)}
                className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-xs">{t('common.previous')}</button>
              <span className="text-sm text-slate-500 dark:text-slate-400">{t('common.page')} {pageNum} {t('common.of')} {page.total_pages}</span>
              <button disabled={pageNum >= page.total_pages} onClick={() => setPageNum(pageNum + 1)}
                className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-xs">{t('common.next')}</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
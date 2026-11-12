import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useStore } from '../contexts/StoreContext';
import { createStore, updateStore, deleteStore, listStoreMembers, createMerchant } from '../api/merchants';
import type { Store, StoreMember } from '../types';
import { Card, Button, Input, Badge, Modal, ConfirmDialog } from '../components/ui';
import { useToast } from '../contexts/ToastContext';

interface StoreForm {
  name: string;
  slug: string;
  domain: string;
  status: 'active' | 'inactive' | 'suspended';
}

const emptyForm: StoreForm = { name: '', slug: '', domain: '', status: 'active' };

export default function Stores() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { merchant, stores, loading, merchantMissing, activeStoreId, setActiveStoreId: selectStore, reload } = useStore();

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Store | null>(null);
  const [form, setForm] = useState<StoreForm>(emptyForm);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [deleting, setDeleting] = useState<Store | null>(null);
  const [merchantModalOpen, setMerchantModalOpen] = useState(false);
  const [companyName, setCompanyName] = useState('');
  const [memberStore, setMemberStore] = useState<Store | null>(null);
  const [members, setMembers] = useState<StoreMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (store: Store) => {
    setEditing(store);
    setForm({
      name: store.name,
      slug: store.slug,
      domain: store.domain || '',
      status: (store.status as StoreForm['status']) || 'active',
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitLoading(true);
    try {
      if (editing) {
        await updateStore(editing.id, form);
        showToast('success', t('stores.updated'));
      } else {
        await createStore(form);
        showToast('success', t('stores.created'));
      }
      setModalOpen(false);
      await reload();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await deleteStore(deleting.id);
      showToast('success', t('stores.deleted'));
      await reload();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    }
  };

  const handleCreateMerchant = async () => {
    if (!companyName.trim()) return;
    setSubmitLoading(true);
    try {
      await createMerchant({ company_name: companyName.trim() });
      showToast('success', t('stores.merchant_created'));
      setMerchantModalOpen(false);
      await reload();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally {
      setSubmitLoading(false);
    }
  };

  const openMembers = async (store: Store) => {
    setMemberStore(store);
    setMembersLoading(true);
    setMembers([]);
    try {
      const res = await listStoreMembers(store.id, { page_size: 100 });
      setMembers(res.items);
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally {
      setMembersLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('stores.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('stores.subtitle')}</p>
        </div>
        {merchant && (
          <Button onClick={openCreate}>{t('stores.add')}</Button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />)}
        </div>
      ) : merchantMissing ? (
        <Card>
          <div className="text-center py-8">
            <div className="mx-auto w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 dark:bg-blue-500/10 dark:text-blue-400">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{t('stores.no_merchant')}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 mb-5">{t('stores.no_merchant_desc')}</p>
            <Button onClick={() => { setCompanyName(''); setMerchantModalOpen(true); }}>
              {t('stores.create_merchant')}
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <Card>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-bold text-lg shadow-sm">
                  {merchant?.company_name?.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="text-base font-semibold text-slate-900 dark:text-slate-100">{merchant?.company_name}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {t('stores.verification_status')}: <Badge variant="cobalt">{merchant?.verification_status ?? ''}</Badge>
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('stores.trust_score')}</p>
                <p className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                  {merchant?.trust_score_ref != null ? merchant.trust_score_ref.toFixed(1) : '—'}
                </p>
              </div>
            </div>
          </Card>

          <Card>
            {stores.length === 0 ? (
              <div className="text-center py-10">
                <p className="text-sm text-slate-400 dark:text-slate-500">{t('stores.no_stores')}</p>
                <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">{t('stores.no_stores_desc')}</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200/90 dark:border-slate-800">
                <table className="min-w-full">
                  <thead className="bg-slate-50/80 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stores.name_col')}</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stores.slug')}</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stores.domain')}</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stores.status')}</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stores.active_store')}</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stores.actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-slate-900 divide-y divide-slate-100 dark:divide-slate-800">
                    {stores.map((store) => (
                      <tr key={store.id} className="hover:bg-blue-50/30 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-slate-100">{store.name}</td>
                        <td className="px-4 py-3 text-xs font-mono text-slate-500 dark:text-slate-400">/{store.slug}</td>
                        <td className="px-4 py-3 text-xs font-mono text-slate-500 dark:text-slate-400">{store.domain || '—'}</td>
                        <td className="px-4 py-3"><Badge>{store.status}</Badge></td>
                        <td className="px-4 py-3">
                          {activeStoreId === store.id ? (
                            <Badge variant="success">{t('stores.current')}</Badge>
                          ) : (
                            <Button size="sm" variant="outline" onClick={() => selectStore(store.id)}>
                              {t('stores.select')}
                            </Button>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button size="sm" variant="ghost" onClick={() => openMembers(store)}>{t('stores.members')}</Button>
                            <Button size="sm" variant="ghost" onClick={() => openEdit(store)}>{t('common.edit')}</Button>
                            <Button size="sm" variant="ghost" className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30" onClick={() => setDeleting(store)}>{t('common.delete')}</Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? t('stores.edit') : t('stores.new')}>
        <div className="space-y-4">
          <Input
            label={t('stores.name')}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder={t('stores.name_placeholder')}
          />
          <Input
            label={t('stores.slug')}
            value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
            placeholder="my-store"
          />
          <Input
            label={t('stores.domain')}
            value={form.domain}
            onChange={(e) => setForm({ ...form, domain: e.target.value })}
            placeholder="https://example.com"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>{t('common.cancel')}</Button>
            <Button onClick={handleSubmit} loading={submitLoading} disabled={!form.name.trim() || !form.slug.trim()}>
              {editing ? t('common.update') : t('common.create')}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={merchantModalOpen} onClose={() => setMerchantModalOpen(false)} title={t('stores.create_merchant')}>
        <div className="space-y-4">
          <Input
            label={t('stores.company_name')}
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder={t('stores.company_name_placeholder')}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setMerchantModalOpen(false)}>{t('common.cancel')}</Button>
            <Button onClick={handleCreateMerchant} loading={submitLoading} disabled={!companyName.trim()}>
              {t('common.create')}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!memberStore} onClose={() => setMemberStore(null)} title={t('stores.members_title', { name: memberStore?.name || '' })}>
        {membersLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-lg" />)}
          </div>
        ) : members.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-6">{t('stores.no_members')}</p>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {members.map((m) => (
              <div key={m.id} className="flex items-center justify-between py-3">
                <p className="text-sm font-medium font-mono text-slate-900 dark:text-slate-100">{m.user_id}</p>
                <Badge variant="cobalt">{m.role}</Badge>
              </div>
            ))}
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        title={t('stores.delete')}
        message={t('stores.delete_confirm', { name: deleting?.name || '' })}
        confirmLabel={t('common.delete')}
        onConfirm={handleDelete}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
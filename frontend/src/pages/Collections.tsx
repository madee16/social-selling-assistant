import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listCollections, createCollection, updateCollection, deleteCollection } from '../api/collections';
import type { Collection, Page } from '../types';
import { useToast } from '../contexts/ToastContext';
import { useStore } from '../contexts/StoreContext';
import { Button, Card, Input, Modal, ConfirmDialog, Badge } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

export default function Collections() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { activeStoreId } = useStore();
  const [page, setPage] = useState<Page<Collection> | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', slug: '', description: '', sort_order: '0', is_visible: true });
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Collection | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCollections({ page: pageNum, page_size: 10 });
      setPage(data);
    } finally { setLoading(false); }
  }, [pageNum]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const resetForm = () => {
    setForm({ name: '', slug: '', description: '', sort_order: '0', is_visible: true });
    setEditId(null);
    setFormOpen(false);
  };

  const openCreate = () => { resetForm(); setFormOpen(true); };

  const openEdit = (c: Collection) => {
    setForm({
      name: c.name,
      slug: c.slug,
      description: c.description || '',
      sort_order: String(c.sort_order),
      is_visible: c.is_visible,
    });
    setEditId(c.id);
    setFormOpen(true);
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const baseSlug = (form.slug.trim() || form.name.trim()).toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/[\s_]+/g, '-');
      const payload = {
        name: form.name.trim(),
        slug: baseSlug || undefined,
        description: form.description.trim() || undefined,
        sort_order: parseInt(form.sort_order) || 0,
        is_visible: form.is_visible,
        store_id: activeStoreId || undefined,
      };
      if (editId) {
        await updateCollection(editId, payload);
        showToast('success', t('collections.updated'));
      } else {
        await createCollection(payload);
        showToast('success', t('collections.created'));
      }
      resetForm();
      fetchData();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally { setSaving(false); }
  };

  const toggleVisibility = async (c: Collection) => {
    try {
      await updateCollection(c.id, { name: c.name, is_visible: !c.is_visible });
      fetchData();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) return;
    try {
      await deleteCollection(confirmDelete.id);
      showToast('success', t('collections.deleted'));
      fetchData();
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    } finally {
      setConfirmDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('collections.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('collections.subtitle')}</p>
        </div>
        <Button onClick={openCreate}>{t('collections.add')}</Button>
      </div>

      <Modal open={formOpen} onClose={resetForm} title={editId ? t('collections.edit') : t('collections.new')}>
        <div className="space-y-4">
          <Input label={`${t('collections.name')} *`} value={form.name} onChange={(e) => { setForm({ ...form, name: e.target.value }); }} />
          <Input label={t('collections.slug')} value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
            placeholder="summer-collection" />
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('collections.description')}</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={t('collections.sort_order')} type="number" value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: e.target.value })} />
            <div className="flex items-end justify-between pb-1">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('collections.visible')}</span>
              <button type="button" onClick={() => setForm({ ...form, is_visible: !form.is_visible })}
                className={`relative w-10 h-5 rounded-full transition-colors ${form.is_visible ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all shadow-xs ${form.is_visible ? 'left-5' : 'left-0.5'}`} />
              </button>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={resetForm}>{t('common.cancel')}</Button>
            <Button onClick={handleSubmit} loading={saving} disabled={!form.name.trim()}>{editId ? t('common.update') : t('common.create')}</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={!!confirmDelete} onClose={() => setConfirmDelete(null)} onConfirm={handleDelete}
        title={t('collections.delete')} message={t('collections.delete_confirm', { name: confirmDelete?.name || '' })} />

      {loading ? (
        <SkeletonTable rows={4} cols={5} />
      ) : !page || page.items.length === 0 ? (
        <Card>
          <div className="text-center py-8">
            <svg className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            <p className="text-slate-600 dark:text-slate-300 font-medium mt-3">{t('collections.no_collections')}</p>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-0.5">{t('collections.no_collections_desc')}</p>
          </div>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {page.items.map((c) => (
              <Card key={c.id} className="flex flex-col hover:border-blue-200 dark:hover:border-slate-700 hover:shadow-md transition-all duration-200">
                <div className="flex items-start justify-between">
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate">{c.name}</h3>
                    <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-0.5">/{c.slug}</p>
                  </div>
                  <Badge variant={c.is_visible ? 'success' : 'default'}>{c.is_visible ? t('collections.visible') : t('collections.hidden')}</Badge>
                </div>
                {c.description && <p className="text-sm text-slate-600 dark:text-slate-300 mt-2 line-clamp-2">{c.description}</p>}
                <div className="mt-4 text-xs font-mono text-slate-400 dark:text-slate-500">
                  {c.store_id ? t('collections.store_id') : t('collections.global')} · {t('collections.order')} {c.sort_order}
                </div>
                <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <Button size="sm" variant="ghost" onClick={() => toggleVisibility(c)}>
                    {c.is_visible ? t('collections.hide') : t('collections.show')}
                  </Button>
                  <div className="flex-1" />
                  <Button size="sm" variant="ghost" onClick={() => openEdit(c)}>{t('common.edit')}</Button>
                  <Button size="sm" variant="ghost" className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30" onClick={() => setConfirmDelete(c)}>{t('common.delete')}</Button>
                </div>
              </Card>
            ))}
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
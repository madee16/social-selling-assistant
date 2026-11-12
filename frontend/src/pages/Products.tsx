import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listProducts, createProduct, updateProduct, deleteProduct, listCategories, importProducts, createCategory } from '../api/products';
import { uploadProductImage } from '../api/uploads';
import type { Product, Category, Page } from '../types';
import { useToast } from '../contexts/ToastContext';
import { Button, Card, Input, Modal, ConfirmDialog, Badge } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

export default function Products() {
  const { t } = useTranslation();
  const [page, setPage] = useState<Page<Product> | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState('');
  const [pageNum, setPageNum] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', price: '', description: '', category_id: '', stock_quantity: '0', image_url: '' });
  const [uploading, setUploading] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importCat, setImportCat] = useState('');
  const [importResult, setImportResult] = useState<string | null>(null);
  const [showCatForm, setShowCatForm] = useState(false);
  const [newCat, setNewCat] = useState('');
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const { showToast } = useToast();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [pData, cats] = await Promise.all([
        listProducts({ page: pageNum, page_size: 10, search: search || undefined, category_id: catFilter || undefined }),
        listCategories(),
      ]);
      setPage(pData);
      setCategories(cats.items);
    } finally { setLoading(false); }
  }, [pageNum, search, catFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const resetForm = () => {
    setForm({ name: '', price: '', description: '', category_id: '', stock_quantity: '0', image_url: '' });
    setEditId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: form.name,
      price: parseFloat(form.price),
      description: form.description || undefined,
      category_id: form.category_id || undefined,
      stock_quantity: parseInt(form.stock_quantity) || 0,
      image_url: form.image_url || undefined,
    };
    if (editId) { await updateProduct(editId, payload); } else { await createProduct(payload); }
    resetForm();
    fetchData();
  };

  const handleEdit = (p: Product) => {
    setForm({ name: p.name, price: String(p.price), description: p.description || '', category_id: p.category_id || '', stock_quantity: String(p.stock_quantity), image_url: p.image_url || '' });
    setEditId(p.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => { await deleteProduct(id); setConfirmDelete(null); fetchData(); };

  const handleImport = async () => {
    if (!importFile) return;
    setImportResult('Uploading...');
    try {
      const res = await importProducts(importFile, importCat || undefined);
      setImportResult(`Imported ${res.imported} products.${res.errors.length ? ' Errors: ' + res.errors.join('; ') : ''}`);
      setImportFile(null);
      fetchData();
    } catch (err) { console.error('Import failed:', err); setImportResult('Import failed'); }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const { url } = await uploadProductImage(file);
      setForm({ ...form, image_url: url });
    } catch (err) { console.error('Failed to upload image:', err); showToast('error', 'Failed to upload image'); } finally { setUploading(false); }
  };

  const handleAddCategory = async () => {
    if (!newCat.trim()) return;
    await createCategory(newCat.trim());
    setNewCat('');
    setShowCatForm(false);
    const cats = await listCategories();
    setCategories(cats.items);
  };

  const getCategoryName = (id: string | null | undefined) => categories.find((c) => c.id === id)?.name || '-';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{t('products.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{t('products.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowImport(!showImport)}>{t('products.import')}</Button>
          <Button onClick={() => { resetForm(); setShowForm(true); }}>{t('products.add')}</Button>
        </div>
      </div>

      {showImport && (
        <Card className="border-blue-200/80 bg-blue-50/50 dark:border-blue-500/20 dark:bg-blue-500/10">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Import Products from Excel/CSV</h3>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">File</label>
              <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                className="text-sm text-slate-700 dark:text-slate-200 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-500/20 dark:file:text-blue-300 dark:hover:file:bg-blue-500/30" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">{t('products.category')} ({t('common.search')})</label>
              <select value={importCat} onChange={(e) => setImportCat(e.target.value)} className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
                <option value="">{t('common.no_results')}</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <Button onClick={handleImport} disabled={!importFile} size="sm">{t('common.search')}</Button>
          </div>
          {importResult && <p className={`text-sm mt-2 font-medium ${importResult.startsWith('Imported') ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}`}>{importResult}</p>}
        </Card>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input placeholder={t('products.search')} value={search} onChange={(e) => { setSearch(e.target.value); setPageNum(1); }}
            className="w-full pl-10 pr-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-all" />
        </div>
        <select value={catFilter} onChange={(e) => { setCatFilter(e.target.value); setPageNum(1); }}
          className="rounded-lg border border-slate-300 dark:border-slate-700 px-3.5 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-all cursor-pointer">
          <option value="">{t('products.all_categories')}</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      <Modal open={showForm} onClose={resetForm} title={editId ? t('products.edit') : t('products.new')}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={`${t('products.name')} *`} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input label={`${t('products.price')} *`} type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('products.category')}</label>
              <div className="flex gap-1.5">
                <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}
                  className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
                  <option value="">{t('common.no_results')}</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <button type="button" onClick={() => setShowCatForm(!showCatForm)} className="text-blue-600 text-sm px-2.5 hover:bg-blue-50 rounded-lg dark:text-blue-400 dark:hover:bg-blue-500/10 font-bold border border-slate-200 dark:border-slate-700 cursor-pointer">+</button>
              </div>
              {showCatForm && (
                <div className="flex gap-1.5 mt-2">
                  <input value={newCat} onChange={(e) => setNewCat(e.target.value)} placeholder={`${t('products.category')} ${t('products.name')}`} className="flex-1 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-sm bg-white dark:bg-slate-800" />
                  <button type="button" onClick={handleAddCategory} className="bg-emerald-600 text-white px-3 py-1 rounded-lg text-sm font-medium cursor-pointer hover:bg-emerald-700">{t('common.create')}</button>
                </div>
              )}
            </div>
            <Input label={t('products.stock')} type="number" value={form.stock_quantity} onChange={(e) => setForm({ ...form, stock_quantity: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Image</label>
              <div className="flex gap-2 items-center">
                <input type="file" accept="image/*" onChange={handleImageUpload}
                  className="text-sm text-slate-700 file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-500/20 dark:file:text-blue-300" />
                {uploading && <span className="text-xs text-blue-600 font-medium">Uploading...</span>}
              </div>
              {form.image_url && (
                <div className="mt-2 flex items-center gap-2">
                  <img src={form.image_url} alt="preview" className="w-12 h-12 rounded-lg object-cover border border-slate-200 dark:border-slate-700 shadow-2xs" />
                  <button type="button" onClick={() => setForm({ ...form, image_url: '' })}
                    className="text-xs text-rose-600 hover:text-rose-800 font-semibold cursor-pointer">Remove</button>
                </div>
              )}
            </div>
            <Input label="Image URL" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} placeholder="Or paste a URL" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('products.description')}</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-all" />
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" type="button" onClick={resetForm}>{t('common.cancel')}</Button>
            <Button type="submit">{editId ? t('common.update') : t('common.create')}</Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog open={!!confirmDelete} onClose={() => setConfirmDelete(null)} onConfirm={() => handleDelete(confirmDelete!)}
        title={t('products.delete')} message={t('products.delete_confirm')} />

      {loading ? (
        <SkeletonTable rows={5} cols={5} />
      ) : !page || page.items.length === 0 ? (
        <Card>
          <div className="text-center py-10">
            <svg className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <p className="text-slate-700 dark:text-slate-300 font-medium mt-3">{t('products.no_products')}</p>
            <p className="text-sm text-slate-400 dark:text-slate-500">{t('products.no_products_desc')}</p>
          </div>
        </Card>
      ) : (
        <>
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200/90 dark:border-slate-800 bg-slate-50/75 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('products.name')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('products.price')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('products.stock')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('products.category')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('products.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {page.items.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {p.image_url && <img src={p.image_url} alt="" className="w-9 h-9 rounded-lg object-cover border border-slate-200 dark:border-slate-700 shrink-0" />}
                          <div>
                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{p.name}</p>
                            {p.description && <p className="text-xs text-slate-400 dark:text-slate-500 truncate max-w-[200px]">{p.description}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm font-bold text-slate-900 dark:text-slate-100">{p.price.toFixed(2)} TND</td>
                      <td className="px-4 py-3">
                        <Badge variant={p.stock_quantity > 10 ? 'success' : p.stock_quantity > 0 ? 'warning' : 'danger'}>{String(p.stock_quantity)}</Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{getCategoryName(p.category_id)}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => handleEdit(p)} className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold mr-3 cursor-pointer">{t('common.edit')}</button>
                        <button onClick={() => setConfirmDelete(p.id)} className="text-sm text-rose-600 hover:text-rose-800 dark:text-rose-400 dark:hover:text-rose-300 font-semibold cursor-pointer">{t('common.delete')}</button>
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
                className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer">{t('common.previous')}</button>
              <span className="text-sm font-medium text-slate-500 dark:text-slate-400">{t('common.page')} {pageNum} {t('common.of')} {page.total_pages}</span>
              <button disabled={pageNum >= page.total_pages} onClick={() => setPageNum(pageNum + 1)}
                className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer">{t('common.next')}</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

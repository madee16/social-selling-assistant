import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listProducts } from '../api/products';
import {
  listAttributeDefs, createAttributeDef, updateAttributeDef, deleteAttributeDef,
  listVariants, createVariant, deleteVariant,
  listInventory, createInventory, updateInventory,
  listPrices, createPrice, updatePrice,
} from '../api/catalog';
import type { AttributeDef, AttributeDefPayload, InventoryRecord, Page, Price, Product, ProductVariant } from '../types';
import { useToast } from '../contexts/ToastContext';
import { useStore } from '../contexts/StoreContext';
import { Button, Card, Input, Modal, ConfirmDialog, Badge } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

type Tab = 'attrs' | 'variants' | 'inventory' | 'prices';

export default function Catalog() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { activeStoreId, stores } = useStore();
  const [tab, setTab] = useState<Tab>('attrs');

  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('');

  // attribute defs
  const [attrs, setAttrs] = useState<Page<AttributeDef> | null>(null);
  const [attrsLoading, setAttrsLoading] = useState(true);
  const [attrModalOpen, setAttrModalOpen] = useState(false);
  const [attrEditId, setAttrEditId] = useState<string | null>(null);
  const [attrForm, setAttrForm] = useState({ name: '', attribute_type: 'text', values: '', is_required: false, is_filterable: false, sort_order: '0' });
  const [attrConfirmDelete, setAttrConfirmDelete] = useState<AttributeDef | null>(null);

  // variants
  const [variants, setVariants] = useState<Page<ProductVariant> | null>(null);
  const [variantsLoading, setVariantsLoading] = useState(false);
  const [variantModalOpen, setVariantModalOpen] = useState(false);
  const [variantForm, setVariantForm] = useState({ sku: '', name: '', options: '', quantity: '0' });

  // inventory
  const [inventory, setInventory] = useState<Page<InventoryRecord> | null>(null);
  const [invLoading, setInvLoading] = useState(false);
  const [invModalOpen, setInvModalOpen] = useState(false);
  const [invEditId, setInvEditId] = useState<string | null>(null);
  const [invForm, setInvForm] = useState({ quantity: '0', reserved_quantity: '0', low_stock_threshold: '5' });

  // prices
  const [prices, setPrices] = useState<Page<Price> | null>(null);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [priceModalOpen, setPriceModalOpen] = useState(false);
  const [priceEditId, setPriceEditId] = useState<string | null>(null);
  const [priceForm, setPriceForm] = useState({ amount: '', currency: 'TND', sale_price: '' });

  const [saving, setSaving] = useState(false);

  const loadProducts = useCallback(async () => {
    try {
      const res = await listProducts({ page_size: 100 });
      setProducts(res.items);
      setSelectedProduct((cur) => cur || res.items[0]?.id || '');
    } catch (err: unknown) {
      showToast('error', (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error'));
    }
  }, [showToast, t]);

  useEffect(() => { loadProducts(); }, [loadProducts]);

  useEffect(() => {
    if (tab === 'attrs') loadAttrs();
  }, [tab]);

  const loadAttrs = async () => {
    setAttrsLoading(true);
    try {
      setAttrs(await listAttributeDefs({ page_size: 100 }));
    } finally { setAttrsLoading(false); }
  };

  useEffect(() => {
    if (tab === 'variants' && selectedProduct) {
      setVariantsLoading(true);
      listVariants(selectedProduct, { page_size: 100 }).then(setVariants).finally(() => setVariantsLoading(false));
    }
  }, [tab, selectedProduct]);

  useEffect(() => {
    if (tab === 'inventory' && selectedProduct) {
      setInvLoading(true);
      listInventory(selectedProduct, { page_size: 100 }).then(setInventory).finally(() => setInvLoading(false));
    }
  }, [tab, selectedProduct]);

  useEffect(() => {
    if (tab === 'prices' && selectedProduct) {
      setPricesLoading(true);
      listPrices(selectedProduct, { page_size: 100 }).then(setPrices).finally(() => setPricesLoading(false));
    }
  }, [tab, selectedProduct]);

  const errMsg = (err: unknown) => (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error');

  // ---- attribute defs ----
  const openAttrCreate = () => {
    setAttrForm({ name: '', attribute_type: 'text', values: '', is_required: false, is_filterable: false, sort_order: '0' });
    setAttrEditId(null);
    setAttrModalOpen(true);
  };

  const openAttrEdit = (a: AttributeDef) => {
    setAttrForm({
      name: a.name,
      attribute_type: a.attribute_type,
      values: (a.values || []).join(', '),
      is_required: a.is_required,
      is_filterable: a.is_filterable,
      sort_order: String(a.sort_order),
    });
    setAttrEditId(a.id);
    setAttrModalOpen(true);
  };

  const saveAttr = async () => {
    setSaving(true);
    try {
      const payload = {
        name: attrForm.name.trim(),
        attribute_type: attrForm.attribute_type as AttributeDefPayload['attribute_type'],
        values: attrForm.values.trim() ? attrForm.values.split(',').map((v) => v.trim()).filter(Boolean) : undefined,
        is_required: attrForm.is_required,
        is_filterable: attrForm.is_filterable,
        sort_order: parseInt(attrForm.sort_order) || 0,
      };
      if (attrEditId) {
        await updateAttributeDef(attrEditId, payload);
        showToast('success', t('catalog.attr_updated'));
      } else {
        await createAttributeDef(payload);
        showToast('success', t('catalog.attr_created'));
      }
      setAttrModalOpen(false);
      await loadAttrs();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const removeAttr = async () => {
    if (!attrConfirmDelete) return;
    try {
      await deleteAttributeDef(attrConfirmDelete.id);
      showToast('success', t('catalog.attr_deleted'));
      await loadAttrs();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally {
      setAttrConfirmDelete(null);
    }
  };

  // ---- variants ----
  const saveVariant = async () => {
    if (!selectedProduct) return;
    setSaving(true);
    try {
      let options: Record<string, unknown> | undefined;
      if (variantForm.options.trim()) {
        try { options = JSON.parse(variantForm.options); } catch { showToast('error', t('catalog.invalid_json')); return; }
      }
      await createVariant(selectedProduct, {
        sku: variantForm.sku.trim() || undefined,
        name: variantForm.name.trim() || undefined,
        options,
        quantity: parseInt(variantForm.quantity) || 0,
      });
      setVariantModalOpen(false);
      setVariantForm({ sku: '', name: '', options: '', quantity: '0' });
      setVariants(await listVariants(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const removeVariant = async (id: string) => {
    if (!selectedProduct) return;
    try {
      await deleteVariant(id);
      setVariants(await listVariants(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    }
  };

  // ---- inventory ----
  const openInvCreate = () => {
    setInvEditId(null);
    setInvForm({ quantity: '0', reserved_quantity: '0', low_stock_threshold: '5' });
    setInvModalOpen(true);
  };

  const openInvEdit = (r: InventoryRecord) => {
    setInvEditId(r.id);
    setInvForm({ quantity: String(r.quantity), reserved_quantity: String(r.reserved_quantity), low_stock_threshold: String(r.low_stock_threshold) });
    setInvModalOpen(true);
  };

  const saveInventory = async () => {
    if (!selectedProduct || !activeStoreId) return;
    setSaving(true);
    try {
      const payload = {
        store_id: activeStoreId,
        quantity: parseInt(invForm.quantity) || 0,
        reserved_quantity: parseInt(invForm.reserved_quantity) || 0,
        low_stock_threshold: parseInt(invForm.low_stock_threshold) || 0,
      };
      if (invEditId) {
        await updateInventory(invEditId, payload);
        showToast('success', t('catalog.inv_updated'));
      } else {
        await createInventory(selectedProduct, payload);
        showToast('success', t('catalog.inv_created'));
      }
      setInvModalOpen(false);
      setInventory(await listInventory(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  // ---- prices ----
  const openPriceCreate = () => {
    setPriceEditId(null);
    setPriceForm({ amount: '', currency: 'TND', sale_price: '' });
    setPriceModalOpen(true);
  };

  const openPriceEdit = (p: Price) => {
    setPriceEditId(p.id);
    setPriceForm({ amount: String(p.amount), currency: p.currency, sale_price: p.sale_price != null ? String(p.sale_price) : '' });
    setPriceModalOpen(true);
  };

  const savePrice = async () => {
    if (!selectedProduct || !activeStoreId) return;
    setSaving(true);
    try {
      const payload = {
        store_id: activeStoreId,
        amount: parseFloat(priceForm.amount),
        currency: priceForm.currency || 'TND',
        sale_price: priceForm.sale_price ? parseFloat(priceForm.sale_price) : undefined,
      };
      if (priceEditId) {
        await updatePrice(priceEditId, payload);
        showToast('success', t('catalog.price_updated'));
      } else {
        await createPrice(selectedProduct, payload);
        showToast('success', t('catalog.price_created'));
      }
      setPriceModalOpen(false);
      setPrices(await listPrices(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const storeName = (id: string) => stores.find((s) => s.id === id)?.name || id.slice(0, 8);
  const lowStock = (r: InventoryRecord) => r.quantity - r.reserved_quantity <= r.low_stock_threshold;

  const tabs: { key: Tab; label: string }[] = [
    { key: 'attrs', label: t('catalog.tab_attrs') },
    { key: 'variants', label: t('catalog.tab_variants') },
    { key: 'inventory', label: t('catalog.tab_inventory') },
    { key: 'prices', label: t('catalog.tab_prices') },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{t('catalog.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{t('catalog.subtitle')}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-700/80">
        {tabs.map((tb) => (
          <button key={tb.key} onClick={() => setTab(tb.key)}
            className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all -mb-px cursor-pointer ${
              tab === tb.key ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}>
            {tb.label}
          </button>
        ))}
        <div className="flex-1" />
        {(tab === 'variants' || tab === 'inventory' || tab === 'prices') && (
          <select value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}
            className="mb-2 rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 max-w-xs dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100 cursor-pointer">
            {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
      </div>

      {!activeStoreId && (tab === 'inventory' || tab === 'prices') && (
        <Card className="border-amber-200 bg-amber-50/70 dark:border-amber-500/20 dark:bg-amber-500/10">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-300">{t('catalog.select_store_hint')}</p>
        </Card>
      )}

      {/* Attribute definitions */}
      {tab === 'attrs' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openAttrCreate}>{t('catalog.add_attr')}</Button>
          </div>
          {attrsLoading ? (
            <SkeletonTable rows={4} cols={4} />
          ) : !attrs || attrs.items.length === 0 ? (
            <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('catalog.no_attrs')}</p></Card>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden dark:bg-slate-900 dark:border-slate-800 shadow-xs">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200/90 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.name')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.type')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.values')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.flags')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {attrs.items.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/70 transition-colors dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{a.name}</td>
                      <td className="px-4 py-3"><Badge variant="info">{a.attribute_type}</Badge></td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{a.values ? a.values.join(', ') : '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {a.is_filterable && <Badge variant="purple">{t('catalog.filterable')}</Badge>}
                          {a.is_required && <Badge variant="warning">{t('catalog.required')}</Badge>}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => openAttrEdit(a)} className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold mr-3 cursor-pointer">{t('common.edit')}</button>
                        <button onClick={() => setAttrConfirmDelete(a)} className="text-sm text-rose-600 hover:text-rose-800 dark:text-rose-400 dark:hover:text-rose-300 font-semibold cursor-pointer">{t('common.delete')}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Modal open={attrModalOpen} onClose={() => setAttrModalOpen(false)} title={attrEditId ? t('catalog.edit_attr') : t('catalog.new_attr')}>
            <div className="space-y-4">
              <Input label={`${t('catalog.name')} *`} value={attrForm.name} onChange={(e) => setAttrForm({ ...attrForm, name: e.target.value })} />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5 dark:text-gray-200">{t('catalog.type')}</label>
                <select value={attrForm.attribute_type} onChange={(e) => setAttrForm({ ...attrForm, attribute_type: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600">
                  {['text', 'number', 'boolean', 'select', 'multi_select'].map((ty) => <option key={ty} value={ty}>{ty}</option>)}
                </select>
              </div>
              <Input label={t('catalog.values_hint')} value={attrForm.values} onChange={(e) => setAttrForm({ ...attrForm, values: e.target.value })} placeholder="red, blue, green" />
              <div className="grid grid-cols-2 gap-4">
                {[{ key: 'is_required' as const, label: t('catalog.required') }, { key: 'is_filterable' as const, label: t('catalog.filterable') }].map((f) => (
                  <div key={f.key} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{f.label}</span>
                    <button type="button" onClick={() => setAttrForm({ ...attrForm, [f.key]: !attrForm[f.key] })}
                      className={`relative w-10 h-5 rounded-full transition-colors ${attrForm[f.key] ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'}`}>
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${attrForm[f.key] ? 'left-5' : 'left-0.5'}`} />
                    </button>
                  </div>
                ))}
              </div>
              <Input label={t('catalog.sort_order')} type="number" value={attrForm.sort_order} onChange={(e) => setAttrForm({ ...attrForm, sort_order: e.target.value })} />
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setAttrModalOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveAttr} loading={saving} disabled={!attrForm.name.trim()}>{attrEditId ? t('common.update') : t('common.create')}</Button>
              </div>
            </div>
          </Modal>
          <ConfirmDialog open={!!attrConfirmDelete} onClose={() => setAttrConfirmDelete(null)} onConfirm={removeAttr}
            title={t('catalog.delete_attr')} message={t('catalog.delete_confirm')} />
        </div>
      )}

      {/* Variants */}
      {tab === 'variants' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => { setVariantForm({ sku: '', name: '', options: '', quantity: '0' }); setVariantModalOpen(true); }} disabled={!selectedProduct}>
              {t('catalog.add_variant')}
            </Button>
          </div>
          {variantsLoading ? <SkeletonTable rows={4} cols={4} />
            : !variants || variants.items.length === 0 ? <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('catalog.no_variants')}</p></Card>
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden dark:bg-slate-900 dark:border-slate-800 shadow-xs">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200/90 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/60">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.name')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">SKU</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.options')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.quantity')}</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {variants.items.map((v) => (
                      <tr key={v.id} className="hover:bg-slate-50/70 transition-colors dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{v.name || '—'}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-500 dark:text-slate-400">{v.sku || '—'}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{v.options ? JSON.stringify(v.options) : '—'}</td>
                        <td className="px-4 py-3"><Badge variant={v.quantity > 0 ? 'success' : 'danger'}>{String(v.quantity)}</Badge></td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => removeVariant(v.id)} className="text-sm text-rose-600 hover:text-rose-800 dark:text-rose-400 dark:hover:text-rose-300 font-semibold cursor-pointer">{t('common.delete')}</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          <Modal open={variantModalOpen} onClose={() => setVariantModalOpen(false)} title={t('catalog.new_variant')}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label={t('catalog.name')} value={variantForm.name} onChange={(e) => setVariantForm({ ...variantForm, name: e.target.value })} />
                <Input label="SKU" value={variantForm.sku} onChange={(e) => setVariantForm({ ...variantForm, sku: e.target.value })} />
              </div>
              <Input label={t('catalog.quantity')} type="number" value={variantForm.quantity} onChange={(e) => setVariantForm({ ...variantForm, quantity: e.target.value })} />
              <Input label={t('catalog.options')} value={variantForm.options} onChange={(e) => setVariantForm({ ...variantForm, options: e.target.value })} placeholder='{"color": "red", "size": "M"}' />
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setVariantModalOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveVariant} loading={saving}>{t('common.create')}</Button>
              </div>
            </div>
          </Modal>
        </div>
      )}

      {/* Inventory */}
      {tab === 'inventory' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openInvCreate} disabled={!selectedProduct || !activeStoreId}>{t('catalog.add_inventory')}</Button>
          </div>
          {invLoading ? <SkeletonTable rows={4} cols={4} />
            : !inventory || inventory.items.length === 0 ? <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('catalog.no_inventory')}</p></Card>
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden dark:bg-slate-900 dark:border-slate-800 shadow-xs">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200/90 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/60">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.store')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.quantity')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.reserved')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.threshold')}</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {inventory.items.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50/70 transition-colors dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{storeName(r.store_id)}</td>
                        <td className="px-4 py-3"><Badge variant={lowStock(r) ? 'warning' : 'success'}>{String(r.quantity)}</Badge></td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{r.reserved_quantity}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{r.low_stock_threshold}</td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => openInvEdit(r)} className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold cursor-pointer">{t('common.edit')}</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          <Modal open={invModalOpen} onClose={() => setInvModalOpen(false)} title={invEditId ? t('catalog.edit_inventory') : t('catalog.new_inventory')}>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <Input label={t('catalog.quantity')} type="number" value={invForm.quantity} onChange={(e) => setInvForm({ ...invForm, quantity: e.target.value })} />
                <Input label={t('catalog.reserved')} type="number" value={invForm.reserved_quantity} onChange={(e) => setInvForm({ ...invForm, reserved_quantity: e.target.value })} />
                <Input label={t('catalog.threshold')} type="number" value={invForm.low_stock_threshold} onChange={(e) => setInvForm({ ...invForm, low_stock_threshold: e.target.value })} />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setInvModalOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveInventory} loading={saving}>{invEditId ? t('common.update') : t('common.create')}</Button>
              </div>
            </div>
          </Modal>
        </div>
      )}

      {/* Prices */}
      {tab === 'prices' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openPriceCreate} disabled={!selectedProduct || !activeStoreId}>{t('catalog.add_price')}</Button>
          </div>
          {pricesLoading ? <SkeletonTable rows={4} cols={4} />
            : !prices || prices.items.length === 0 ? <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('catalog.no_prices')}</p></Card>
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden dark:bg-slate-900 dark:border-slate-800 shadow-xs">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200/90 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/60">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.store')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.amount')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.sale_price')}</th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.currency')}</th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400">{t('catalog.actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {prices.items.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-50/70 transition-colors dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{storeName(p.store_id)}</td>
                        <td className="px-4 py-3 text-sm font-bold text-slate-900 dark:text-slate-100">{p.amount.toFixed(2)} {p.currency}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{p.sale_price != null ? `${p.sale_price.toFixed(2)} ${p.currency}` : '—'}</td>
                        <td className="px-4 py-3"><Badge variant="info">{p.currency}</Badge></td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => openPriceEdit(p)} className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold cursor-pointer">{t('common.edit')}</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          <Modal open={priceModalOpen} onClose={() => setPriceModalOpen(false)} title={priceEditId ? t('catalog.edit_price') : t('catalog.new_price')}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label={`${t('catalog.amount')} *`} type="number" step="0.01" value={priceForm.amount} onChange={(e) => setPriceForm({ ...priceForm, amount: e.target.value })} />
                <Input label={t('catalog.currency')} value={priceForm.currency} onChange={(e) => setPriceForm({ ...priceForm, currency: e.target.value })} />
              </div>
              <Input label={t('catalog.sale_price')} type="number" step="0.01" value={priceForm.sale_price} onChange={(e) => setPriceForm({ ...priceForm, sale_price: e.target.value })} />
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setPriceModalOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={savePrice} loading={saving} disabled={!priceForm.amount}>{priceEditId ? t('common.update') : t('common.create')}</Button>
              </div>
            </div>
          </Modal>
        </div>
      )}
    </div>
  );
}
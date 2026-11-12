import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { listProducts } from '../api/products';
import {
  listSeoData, createSeoData, updateSeoData, deleteSeoData, listSeoScores,
  generateAiSeo, getShareUrl,
  listMarketplaceListings, createMarketplaceListing, updateMarketplaceListing, deleteMarketplaceListing,
  listProductScores, createProductScore, deleteProductScore,
  listSellerTrust, createSellerTrust, updateSellerTrust, deleteSellerTrust,
} from '../api/marketplace';
import type { MarketplaceListing, MarketplaceListingPayload, Page, Product, ProductScore, SellerTrustScore, SeoData, SeoScore } from '../types';
import { useToast } from '../contexts/ToastContext';
import { useStore } from '../contexts/StoreContext';
import { Button, Card, Input, Modal, ConfirmDialog, Badge } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

type Tab = 'seo' | 'scores' | 'listings' | 'trust';

const scoreColor = (s: number) => (s >= 80 ? 'success' : s >= 50 ? 'warning' : 'danger');

/** Horizontal progress bar for a 0–100 score */
function ScoreBar({ value, label }: { value: number | null; label: string }) {
  const v = value ?? 0;
  const color = v >= 80 ? 'bg-emerald-500' : v >= 50 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
        <span>{label}</span>
        <span className="font-semibold text-slate-700 dark:text-slate-200">{Math.round(v)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

export default function SeoMarketplace() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { activeStoreId, stores } = useStore();
  const [tab, setTab] = useState<Tab>('seo');

  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [saving, setSaving] = useState(false);

  // SEO data
  const [seo, setSeo] = useState<Page<SeoData> | null>(null);
  const [seoLoading, setSeoLoading] = useState(true);
  const [seoFormOpen, setSeoFormOpen] = useState(false);
  const [seoEditId, setSeoEditId] = useState<string | null>(null);
  const [seoForm, setSeoForm] = useState({ entity_type: 'product', entity_id: '', title: '', description: '', keywords: '', slug: '', canonical_url: '', is_indexable: true });
  const [seoConfirmDelete, setSeoConfirmDelete] = useState<SeoData | null>(null);
  const [scoreView, setScoreView] = useState<{ seo: SeoData; scores: SeoScore[] } | null>(null);
  const [optimizingId, setOptimizingId] = useState<string | null>(null);

  // Product scores
  const [scores, setScores] = useState<Page<ProductScore> | null>(null);
  const [scoresLoading, setScoresLoading] = useState(false);
  const [scoreFormOpen, setScoreFormOpen] = useState(false);
  const [scoreForm, setScoreForm] = useState({ score_type: 'ai', score: '0' });

  // Listings
  const [listings, setListings] = useState<Page<MarketplaceListing> | null>(null);
  const [listingsLoading, setListingsLoading] = useState(false);
  const [listingFormOpen, setListingFormOpen] = useState(false);
  const [listingForm, setListingForm] = useState({ marketplace: '', marketplace_product_id: '', listing_status: 'draft', sync_status: 'pending' });

  // Seller trust
  const [trust, setTrust] = useState<Page<SellerTrustScore> | null>(null);
  const [trustLoading, setTrustLoading] = useState(true);
  const [trustFormOpen, setTrustFormOpen] = useState(false);
  const [trustEditId, setTrustEditId] = useState<string | null>(null);
  const [trustForm, setTrustForm] = useState({ score: '0', level: 'bronze', components: '' });
  const [trustConfirmDelete, setTrustConfirmDelete] = useState<SellerTrustScore | null>(null);

  const errMsg = (err: unknown) => (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || t('common.error');
  const storeName = (id: string) => stores.find((s) => s.id === id)?.name || id.slice(0, 8);

  const loadProducts = useCallback(async () => {
    try {
      const res = await listProducts({ page_size: 100 });
      setProducts(res.items);
      setSelectedProduct((cur) => cur || res.items[0]?.id || '');
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    }
  }, [showToast, t]);

  useEffect(() => { loadProducts(); }, [loadProducts]);

  const loadSeo = useCallback(async () => {
    setSeoLoading(true);
    try {
      setSeo(await listSeoData({ page_size: 100 }));
    } finally { setSeoLoading(false); }
  }, []);

  const loadTrust = useCallback(async () => {
    setTrustLoading(true);
    try {
      setTrust(await listSellerTrust({ page_size: 100 }));
    } finally { setTrustLoading(false); }
  }, []);

  useEffect(() => {
    if (tab === 'seo') loadSeo();
    if (tab === 'trust') loadTrust();
  }, [tab, loadSeo, loadTrust]);

  useEffect(() => {
    if (tab === 'scores' && selectedProduct) {
      setScoresLoading(true);
      listProductScores(selectedProduct, { page_size: 100 }).then(setScores).finally(() => setScoresLoading(false));
    }
  }, [tab, selectedProduct]);

  useEffect(() => {
    if (tab === 'listings' && selectedProduct) {
      setListingsLoading(true);
      listMarketplaceListings(selectedProduct, { page_size: 100 }).then(setListings).finally(() => setListingsLoading(false));
    }
  }, [tab, selectedProduct]);

  // ---- SEO ----
  const openSeoCreate = () => {
    setSeoForm({ entity_type: 'product', entity_id: '', title: '', description: '', keywords: '', slug: '', canonical_url: '', is_indexable: true });
    setSeoEditId(null);
    setSeoFormOpen(true);
  };

  const openSeoEdit = (s: SeoData) => {
    setSeoForm({
      entity_type: s.entity_type,
      entity_id: s.entity_id,
      title: s.title || '',
      description: s.description || '',
      keywords: (s.keywords || []).join(', '),
      slug: s.slug || '',
      canonical_url: s.canonical_url || '',
      is_indexable: s.is_indexable,
    });
    setSeoEditId(s.id);
    setSeoFormOpen(true);
  };

  const saveSeo = async () => {
    setSaving(true);
    try {
      const payload = {
        entity_type: seoForm.entity_type,
        entity_id: seoForm.entity_id.trim(),
        title: seoForm.title.trim() || undefined,
        description: seoForm.description.trim() || undefined,
        keywords: seoForm.keywords.trim() ? seoForm.keywords.split(',').map((k) => k.trim()).filter(Boolean) : undefined,
        slug: seoForm.slug.trim() || undefined,
        canonical_url: seoForm.canonical_url.trim() || undefined,
        is_indexable: seoForm.is_indexable,
      };
      if (seoEditId) {
        await updateSeoData(seoEditId, payload);
        showToast('success', t('seo.updated'));
      } else {
        await createSeoData(payload);
        showToast('success', t('seo.created'));
      }
      setSeoFormOpen(false);
      await loadSeo();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const removeSeo = async () => {
    if (!seoConfirmDelete) return;
    try {
      await deleteSeoData(seoConfirmDelete.id);
      showToast('success', t('seo.deleted'));
      await loadSeo();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSeoConfirmDelete(null); }
  };

  const viewScores = async (s: SeoData) => {
    try {
      const res = await listSeoScores(s.id, { page_size: 50 });
      setScoreView({ seo: s, scores: res.items });
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    }
  };

  const handleAutoOptimize = async (entityType: string, entityId: string, refreshScoresFor?: SeoData) => {
    if (entityType !== 'product' && entityType !== 'store') {
      showToast('error', 'Optimization is only available for products and stores.');
      return;
    }
    setOptimizingId(entityId);
    try {
      const res = await generateAiSeo(entityType, entityId);
      showToast('success', res.message || t('seo.auto_optimized'));
      await loadSeo();
      if (refreshScoresFor) {
        const scoreRes = await listSeoScores(refreshScoresFor.id, { page_size: 50 });
        setScoreView({ seo: res.seo_data || refreshScoresFor, scores: scoreRes.items });
      }
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally {
      setOptimizingId(null);
    }
  };

  const handleCopyShareLink = async (s: SeoData) => {
    const shareUrl = getShareUrl(s.entity_type, s.slug || s.entity_id);
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
      } else {
        const el = document.createElement('textarea');
        el.value = shareUrl;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
      showToast('success', `${t('seo.share_link_copied')} (${shareUrl})`);
    } catch {
      showToast('info', shareUrl);
    }
  };


  // ---- Scores ----
  const saveScore = async () => {
    if (!selectedProduct || !activeStoreId) return;
    setSaving(true);
    try {
      await createProductScore(selectedProduct, {
        store_id: activeStoreId,
        score_type: scoreForm.score_type,
        score: parseFloat(scoreForm.score),
      });
      setScoreFormOpen(false);
      setScoreForm({ score_type: 'ai', score: '0' });
      setScores(await listProductScores(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const removeScore = async (id: string) => {
    if (!selectedProduct) return;
    try {
      await deleteProductScore(id);
      setScores(await listProductScores(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    }
  };

  // ---- Listings ----
  const saveListing = async () => {
    if (!selectedProduct || !activeStoreId) return;
    setSaving(true);
    try {
      await createMarketplaceListing(selectedProduct, {
        store_id: activeStoreId,
        marketplace: listingForm.marketplace.trim(),
        marketplace_product_id: listingForm.marketplace_product_id.trim() || undefined,
        listing_status: listingForm.listing_status as MarketplaceListingPayload['listing_status'],
        sync_status: listingForm.sync_status as MarketplaceListingPayload['sync_status'],
      });
      setListingFormOpen(false);
      setListingForm({ marketplace: '', marketplace_product_id: '', listing_status: 'draft', sync_status: 'pending' });
      setListings(await listMarketplaceListings(selectedProduct, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const changeListingStatus = async (l: MarketplaceListing, status: MarketplaceListingPayload['listing_status']) => {
    try {
      await updateMarketplaceListing(l.id, { listing_status: status });
      setListings(await listMarketplaceListings(l.product_id, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    }
  };

  const removeListing = async (l: MarketplaceListing) => {
    try {
      await deleteMarketplaceListing(l.id);
      setListings(await listMarketplaceListings(l.product_id, { page_size: 100 }));
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    }
  };

  // ---- Trust ----
  const openTrustCreate = () => {
    setTrustForm({ score: '0', level: 'bronze', components: '' });
    setTrustEditId(null);
    setTrustFormOpen(true);
  };

  const openTrustEdit = (r: SellerTrustScore) => {
    setTrustForm({
      score: String(r.score),
      level: r.level,
      components: r.components ? JSON.stringify(r.components) : '',
    });
    setTrustEditId(r.id);
    setTrustFormOpen(true);
  };

  const saveTrust = async () => {
    setSaving(true);
    try {
      let components: Record<string, unknown> | undefined;
      if (trustForm.components.trim()) {
        try { components = JSON.parse(trustForm.components); } catch { showToast('error', t('catalog.invalid_json')); return; }
      }
      const payload = { score: parseFloat(trustForm.score), level: trustForm.level, components };
      if (trustEditId) {
        await updateSellerTrust(trustEditId, payload);
        showToast('success', t('seo.trust_updated'));
      } else {
        await createSellerTrust(payload);
        showToast('success', t('seo.trust_created'));
      }
      setTrustFormOpen(false);
      await loadTrust();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setSaving(false); }
  };

  const removeTrust = async () => {
    if (!trustConfirmDelete) return;
    try {
      await deleteSellerTrust(trustConfirmDelete.id);
      showToast('success', t('seo.trust_deleted'));
      await loadTrust();
    } catch (err: unknown) {
      showToast('error', errMsg(err));
    } finally { setTrustConfirmDelete(null); }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'seo', label: t('seo.tab_seo') },
    { key: 'scores', label: t('seo.tab_scores') },
    { key: 'listings', label: t('seo.tab_listings') },
    { key: 'trust', label: t('seo.tab_trust') },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('seo.title')}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('seo.subtitle')}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800">
        {tabs.map((tb) => (
          <button key={tb.key} onClick={() => setTab(tb.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === tb.key ? 'border-blue-600 text-blue-600 dark:text-blue-400 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}>
            {tb.label}
          </button>
        ))}
        <div className="flex-1" />
        {(tab === 'scores' || tab === 'listings') && (
          <select value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}
            className="mb-2 rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 max-w-xs dark:bg-slate-800 dark:border-slate-700">
            {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
      </div>

      {!activeStoreId && (tab === 'scores' || tab === 'listings') && (
        <Card className="border-amber-200 bg-amber-50/70 dark:bg-amber-950/20 dark:border-amber-900/40">
          <p className="text-sm text-amber-800 dark:text-amber-300 font-medium">{t('catalog.select_store_hint')}</p>
        </Card>
      )}

      {/* SEO data */}
      {tab === 'seo' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openSeoCreate}>{t('seo.add')}</Button>
          </div>
          {/* Stats strip — only shown when data is loaded */}
          {!seoLoading && seo && seo.items.length > 0 && (
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Total SEO Entries', value: seo.total, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/30' },
                { label: 'Indexed', value: seo.items.filter((s) => s.is_indexable).length, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/30' },
                { label: 'No-Index', value: seo.items.filter((s) => !s.is_indexable).length, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50/70 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30' },
              ].map((stat) => (
                <div key={stat.label} className={`${stat.bg} rounded-xl p-4 shadow-xs`}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{stat.label}</p>
                  <p className={`text-2xl font-bold tracking-tight mt-1 ${stat.color}`}>{stat.value}</p>
                </div>
              ))}
            </div>
          )}
          {seoLoading ? <SkeletonTable rows={4} cols={5} />
            : !seo || seo.items.length === 0 ? (
              <Card>
                <div className="text-center py-10">
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-2 font-medium">{t('seo.no_data')}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    Run <code className="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded font-mono text-xs text-blue-600 dark:text-blue-400">python scripts/seed_demo_seo.py</code> to populate demo data
                  </p>
                </div>
              </Card>
            )
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.entity')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">SEO Title / Slug</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.keywords')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.indexable')}</th>
                        <th className="text-right pl-4 pr-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.actions')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {seo.items.map((s) => (
                        <tr key={s.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3 whitespace-nowrap"><Badge variant="cobalt">{s.entity_type}</Badge></td>
                          <td className="px-4 py-3 max-w-[220px]">
                            <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate" title={s.title || undefined}>{s.title || '—'}</p>
                            {s.slug && <p className="text-xs text-blue-600 dark:text-blue-400 font-mono truncate" title={s.slug}>/{s.slug}</p>}
                            {s.description && (
                              <p className="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5" title={s.description}>
                                {s.description.length > 60 ? s.description.slice(0, 60) + '…' : s.description}
                              </p>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400 max-w-[140px] truncate" title={s.keywords ? s.keywords.join(', ') : undefined}>
                            {s.keywords ? s.keywords.join(', ') : '—'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap"><Badge variant={s.is_indexable ? 'success' : 'default'}>{s.is_indexable ? t('seo.yes') : t('seo.no')}</Badge></td>
                          <td className="pl-4 pr-6 py-3 text-right">
                            <div className="flex items-center justify-end gap-2 flex-wrap">
                              {(s.entity_type === 'product' || s.entity_type === 'store') && (
                                <button
                                  onClick={() => handleAutoOptimize(s.entity_type, s.entity_id)}
                                  disabled={optimizingId === s.entity_id}
                                  className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-950/40 dark:text-blue-300 dark:hover:bg-blue-900/60 disabled:opacity-50 transition-colors whitespace-nowrap cursor-pointer"
                                >
                                  {optimizingId === s.entity_id ? '✨ ...' : `✨ ${t('seo.auto_optimize')}`}
                                </button>
                              )}
                              <button
                                onClick={() => handleCopyShareLink(s)}
                                className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md font-medium bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-300 dark:hover:bg-emerald-900/60 transition-colors whitespace-nowrap cursor-pointer"
                              >
                                🔗 {t('seo.copy_share_link')}
                              </button>
                              <button
                                onClick={() => viewScores(s)}
                                className="text-xs px-2.5 py-1 rounded-md font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/50 transition-colors whitespace-nowrap cursor-pointer"
                              >
                                {t('seo.scores')}
                              </button>
                              <button
                                onClick={() => openSeoEdit(s)}
                                className="text-xs px-2.5 py-1 rounded-md font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/50 transition-colors whitespace-nowrap cursor-pointer"
                              >
                                {t('common.edit')}
                              </button>
                              <button
                                onClick={() => setSeoConfirmDelete(s)}
                                className="text-xs px-2.5 py-1 rounded-md font-medium text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/50 transition-colors whitespace-nowrap cursor-pointer"
                              >
                                {t('common.delete')}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          <Modal open={seoFormOpen} onClose={() => setSeoFormOpen(false)} title={seoEditId ? t('seo.edit') : t('seo.new')}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('seo.entity')}</label>
                  <select value={seoForm.entity_type} onChange={(e) => setSeoForm({ ...seoForm, entity_type: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:border-slate-700">
                    {['product', 'category', 'collection', 'store', 'page'].map((ty) => <option key={ty} value={ty}>{ty}</option>)}
                  </select>
                </div>
                <Input label={`${t('seo.entity_id')} *`} value={seoForm.entity_id} onChange={(e) => setSeoForm({ ...seoForm, entity_id: e.target.value })} placeholder="uuid" />
              </div>
              <Input label={t('seo.title')} value={seoForm.title} onChange={(e) => setSeoForm({ ...seoForm, title: e.target.value })} />
              <Input label={t('seo.keywords')} value={seoForm.keywords} onChange={(e) => setSeoForm({ ...seoForm, keywords: e.target.value })} placeholder="keyword1, keyword2" />
              <div className="grid grid-cols-2 gap-4">
                <Input label={t('seo.slug')} value={seoForm.slug} onChange={(e) => setSeoForm({ ...seoForm, slug: e.target.value })} />
                <Input label={t('seo.canonical')} value={seoForm.canonical_url} onChange={(e) => setSeoForm({ ...seoForm, canonical_url: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('seo.description')}</label>
                <textarea value={seoForm.description} onChange={(e) => setSeoForm({ ...seoForm, description: e.target.value })} rows={3}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:border-slate-700 dark:bg-slate-800" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{t('seo.indexable')}</span>
                <button type="button" onClick={() => setSeoForm({ ...seoForm, is_indexable: !seoForm.is_indexable })}
                  className={`relative w-10 h-5 rounded-full transition-colors ${seoForm.is_indexable ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all shadow-xs ${seoForm.is_indexable ? 'left-5' : 'left-0.5'}`} />
                </button>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setSeoFormOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveSeo} loading={saving} disabled={!seoForm.entity_id.trim()}>{seoEditId ? t('common.update') : t('common.create')}</Button>
              </div>
            </div>
          </Modal>
          <Modal open={!!scoreView} onClose={() => setScoreView(null)} title={`${t('seo.scores')} — ${scoreView?.seo.title || scoreView?.seo.entity_type}`}>
            {scoreView && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-blue-50/70 border border-blue-100 rounded-xl dark:bg-blue-950/30 dark:border-blue-900/40">
                  <div>
                    <p className="text-xs font-semibold text-blue-900 dark:text-blue-200">AI Scoring & Live Sync</p>
                    <p className="text-xs text-blue-700/80 dark:text-blue-400">Régénère le titre, description et recalcule les scores</p>
                  </div>
                  <div className="flex gap-2">
                    {(scoreView.seo.entity_type === 'product' || scoreView.seo.entity_type === 'store') && (
                      <Button
                        variant="secondary"
                        size="sm"
                        loading={optimizingId === scoreView.seo.entity_id}
                        onClick={() => handleAutoOptimize(scoreView.seo.entity_type, scoreView.seo.entity_id, scoreView.seo)}
                      >
                        ✨ {t('seo.auto_optimize')}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopyShareLink(scoreView.seo)}
                    >
                      🔗 {t('seo.copy_share_link')}
                    </Button>
                  </div>
                </div>

                {scoreView.scores.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-sm text-slate-400 dark:text-slate-500 mb-1">{t('seo.no_scores')}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">Cliquez sur "{t('seo.auto_optimize')}" ci-dessus pour calculer les scores.</p>
                  </div>
                ) : (
                  scoreView.scores.map((sc) => (
                    <div key={sc.id} className="border border-slate-200/90 rounded-xl p-4 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-850">
                      {/* Overall badge + big number */}
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <p className="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wide font-semibold">{t('seo.overall')}</p>
                          <p className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{sc.overall_score != null ? Math.round(sc.overall_score) : '—'}</p>
                        </div>
                        <Badge variant={scoreColor(sc.overall_score ?? 0)}>
                          {sc.overall_score != null
                            ? sc.overall_score >= 80 ? '🟢 Good' : sc.overall_score >= 50 ? '🟡 Fair' : '🔴 Poor'
                            : '—'}
                        </Badge>
                      </div>
                      {/* Score bars */}
                      <div className="space-y-3">
                        <ScoreBar value={sc.keyword_score} label={t('seo.keywords')} />
                        <ScoreBar value={sc.meta_score} label={t('seo.meta')} />
                        <ScoreBar value={sc.structure_score} label={t('seo.structure')} />
                      </div>
                      {sc.calculated_at && (
                        <p className="text-xs text-slate-400 dark:text-slate-500 mt-3 text-right">
                          Calculated {new Date(sc.calculated_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </Modal>
          <ConfirmDialog open={!!seoConfirmDelete} onClose={() => setSeoConfirmDelete(null)} onConfirm={removeSeo}
            title={t('seo.delete')} message={t('seo.delete_confirm')} />
        </div>
      )}

      {/* Product scores */}
      {tab === 'scores' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => { setScoreForm({ score_type: 'ai', score: '0' }); setScoreFormOpen(true); }} disabled={!selectedProduct || !activeStoreId}>
              {t('seo.add_score')}
            </Button>
          </div>
          {scoresLoading ? <SkeletonTable rows={4} cols={4} />
            : !scores || scores.items.length === 0 ? <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('seo.no_scores')}</p></Card>
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('catalog.store')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.score')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.score_type')}</th>
                        <th className="text-right pl-4 pr-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.actions')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {scores.items.map((s) => (
                        <tr key={s.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">{storeName(s.store_id)}</td>
                          <td className="px-4 py-3 whitespace-nowrap"><Badge variant={scoreColor(s.score)}>{String(Math.round(s.score))}</Badge></td>
                          <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">{s.score_type}</td>
                          <td className="pl-4 pr-6 py-3 text-right whitespace-nowrap">
                            <button onClick={() => removeScore(s.id)} className="text-sm text-rose-600 hover:text-rose-700 dark:text-rose-400 font-medium cursor-pointer">{t('common.delete')}</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          <Modal open={scoreFormOpen} onClose={() => setScoreFormOpen(false)} title={t('seo.new_score')}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label={`${t('seo.score')} *`} type="number" min={0} max={100} value={scoreForm.score} onChange={(e) => setScoreForm({ ...scoreForm, score: e.target.value })} />
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('seo.score_type')}</label>
                  <select value={scoreForm.score_type} onChange={(e) => setScoreForm({ ...scoreForm, score_type: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:border-slate-700">
                    {['ai', 'manual', 'relevance', 'quality'].map((ty) => <option key={ty} value={ty}>{ty}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setScoreFormOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveScore} loading={saving} disabled={!scoreForm.score}>{t('common.create')}</Button>
              </div>
            </div>
          </Modal>
        </div>
      )}

      {/* Listings */}
      {tab === 'listings' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => { setListingForm({ marketplace: '', marketplace_product_id: '', listing_status: 'draft', sync_status: 'pending' }); setListingFormOpen(true); }}
              disabled={!selectedProduct || !activeStoreId}>{t('seo.add_listing')}</Button>
          </div>
          {listingsLoading ? <SkeletonTable rows={4} cols={4} />
            : !listings || listings.items.length === 0 ? <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('seo.no_listings')}</p></Card>
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('catalog.store')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.marketplace')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.listing_status')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.sync_status')}</th>
                        <th className="text-right pl-4 pr-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.actions')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {listings.items.map((l) => (
                        <tr key={l.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">{storeName(l.store_id)}</td>
                          <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 font-medium whitespace-nowrap">{l.marketplace}</td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <select value={l.listing_status} onChange={(e) => changeListingStatus(l, e.target.value as MarketplaceListingPayload['listing_status'])}
                              className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs bg-white text-slate-800 dark:text-slate-200 dark:bg-slate-800 dark:border-slate-700 focus:ring-2 focus:ring-blue-500/20">
                              {['draft', 'active', 'inactive', 'archived'].map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <Badge variant={l.sync_status === 'synced' ? 'success' : l.sync_status === 'failed' ? 'coral' : 'warning'}>{l.sync_status}</Badge>
                          </td>
                          <td className="pl-4 pr-6 py-3 text-right whitespace-nowrap">
                            <button onClick={() => removeListing(l)} className="text-sm text-rose-600 hover:text-rose-700 dark:text-rose-400 font-medium cursor-pointer">{t('common.delete')}</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          <Modal open={listingFormOpen} onClose={() => setListingFormOpen(false)} title={t('seo.new_listing')}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label={`${t('seo.marketplace')} *`} value={listingForm.marketplace} onChange={(e) => setListingForm({ ...listingForm, marketplace: e.target.value })} placeholder="Jumia" />
                <Input label={t('seo.marketplace_product_id')} value={listingForm.marketplace_product_id} onChange={(e) => setListingForm({ ...listingForm, marketplace_product_id: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('seo.listing_status')}</label>
                  <select value={listingForm.listing_status} onChange={(e) => setListingForm({ ...listingForm, listing_status: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:border-slate-700">
                    {['draft', 'active', 'inactive', 'archived'].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('seo.sync_status')}</label>
                  <select value={listingForm.sync_status} onChange={(e) => setListingForm({ ...listingForm, sync_status: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:border-slate-700">
                    {['pending', 'synced', 'failed'].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setListingFormOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveListing} loading={saving} disabled={!listingForm.marketplace.trim()}>{t('common.create')}</Button>
              </div>
            </div>
          </Modal>
        </div>
      )}

      {/* Seller trust */}
      {tab === 'trust' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={openTrustCreate}>{t('seo.add_trust')}</Button>
          </div>
          {trustLoading ? <SkeletonTable rows={4} cols={4} />
            : !trust || trust.items.length === 0 ? <Card><p className="text-sm text-slate-400 text-center py-8 dark:text-slate-500">{t('seo.no_trust')}</p></Card>
            : (
              <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden shadow-xs dark:bg-slate-900 dark:border-slate-800">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-800/60">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.level')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.score')}</th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.calculated')}</th>
                        <th className="text-right pl-4 pr-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 whitespace-nowrap">{t('seo.actions')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {trust.items.map((r) => (
                        <tr key={r.id} className="hover:bg-blue-50/30 transition-colors dark:hover:bg-slate-800/40">
                          <td className="px-4 py-3 whitespace-nowrap"><Badge variant="purple">{r.level}</Badge></td>
                          <td className="px-4 py-3 whitespace-nowrap"><Badge variant={scoreColor(r.score)}>{String(Math.round(r.score))}</Badge></td>
                          <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">{r.calculated_at ? new Date(r.calculated_at).toLocaleDateString() : '—'}</td>
                          <td className="pl-4 pr-6 py-3 text-right whitespace-nowrap">
                            <button onClick={() => openTrustEdit(r)} className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium mr-3 cursor-pointer">{t('common.edit')}</button>
                            <button onClick={() => setTrustConfirmDelete(r)} className="text-sm text-rose-600 hover:text-rose-700 dark:text-rose-400 font-medium cursor-pointer">{t('common.delete')}</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          <Modal open={trustFormOpen} onClose={() => setTrustFormOpen(false)} title={trustEditId ? t('seo.edit_trust') : t('seo.new_trust')}>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label={`${t('seo.score')} *`} type="number" min={0} max={100} value={trustForm.score} onChange={(e) => setTrustForm({ ...trustForm, score: e.target.value })} />
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('seo.level')}</label>
                  <select value={trustForm.level} onChange={(e) => setTrustForm({ ...trustForm, level: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:border-slate-700">
                    {['bronze', 'silver', 'gold', 'platinum'].map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
              </div>
              <Input label={t('seo.components')} value={trustForm.components} onChange={(e) => setTrustForm({ ...trustForm, components: e.target.value })} placeholder='{"delivery": 90, "quality": 85}' />
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setTrustFormOpen(false)}>{t('common.cancel')}</Button>
                <Button onClick={saveTrust} loading={saving} disabled={!trustForm.score}>{trustEditId ? t('common.update') : t('common.create')}</Button>
              </div>
            </div>
          </Modal>
          <ConfirmDialog open={!!trustConfirmDelete} onClose={() => setTrustConfirmDelete(null)} onConfirm={removeTrust}
            title={t('seo.delete_trust')} message={t('seo.delete_confirm')} />
        </div>
      )}
    </div>
  );
}
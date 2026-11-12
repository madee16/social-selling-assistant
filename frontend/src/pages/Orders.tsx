import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { listOrders, getOrder, updateOrderStatus, deleteOrder, downloadOrderInvoicePdf } from '../api/orders';
import type { Order, OrderListResponse } from '../types';
import { useToast } from '../contexts/ToastContext';
import { Badge, Modal, ConfirmDialog } from '../components/ui';
import { SkeletonTable } from '../components/ui/Skeleton';

const STATUSES = ['pending', 'confirmed', 'preparing', 'shipped', 'delivered', 'cancelled'];

const BADGE_VARIANTS: Record<string, 'warning' | 'info' | 'purple' | 'indigo' | 'success' | 'danger'> = {
  pending: 'warning', confirmed: 'info', preparing: 'purple', shipped: 'indigo', delivered: 'success', cancelled: 'danger',
};

export default function Orders() {
  const { t } = useTranslation();
  const [page, setPage] = useState<OrderListResponse | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const { showToast } = useToast();
  const fetchingRef = useRef(false);

  const handleDownloadPdf = async (orderId: string) => {
    setDownloadingId(orderId);
    try {
      await downloadOrderInvoicePdf(orderId);
      showToast('success', `${t('orders.download_pdf')} - OK`);
    } catch (err) {
      console.error('Failed to download invoice PDF:', err);
      showToast('error', 'Failed to download invoice PDF');
    } finally {
      setDownloadingId(null);
    }
  };

  const fetchData = useCallback(async (isRefresh = false) => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    if (isRefresh) setRefreshing(true); else setLoading(true);
    try {
      const data = await listOrders({ page: pageNum, page_size: 10, status: statusFilter || undefined });
      setPage(data);
    } catch (err) { console.error('Failed to load orders:', err); showToast('error', 'Failed to load orders'); } finally {
      fetchingRef.current = false; setLoading(false); setRefreshing(false);
    }
  }, [pageNum, statusFilter, showToast]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    const handleVisibility = () => { if (!document.hidden) fetchData(true); };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [fetchData]);

  const handleStatusChange = async (orderId: string, newStatus: string) => {
    setUpdatingId(orderId);
    try {
      const updated = await updateOrderStatus(orderId, newStatus);
      showToast('success', 'Order status updated');
      fetchData();
      if (selectedOrder?.id === orderId) setSelectedOrder(updated);
    } catch (err) { console.error('Failed to update order status:', err); showToast('error', 'Failed to update status'); } finally { setUpdatingId(null); }
  };

  const handleDelete = async (id: string) => {
    try { await deleteOrder(id); showToast('success', 'Order deleted'); setConfirmDelete(null); fetchData(); }
    catch (err) { console.error('Failed to delete order:', err); showToast('error', 'Failed to delete order'); }
  };

  const openDetail = async (id: string) => {
    try { const order = await getOrder(id); setSelectedOrder(order); setShowDetail(true); }
    catch (err) { console.error('Failed to load order details:', err); showToast('error', 'Failed to load order details'); }
  };

  if (loading && !page) return <SkeletonTable rows={5} cols={7} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{t('orders.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{t('orders.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPageNum(1); }}
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3.5 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-all cursor-pointer">
            <option value="">{t('orders.all_statuses')}</option>
            {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
          </select>
          {refreshing && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
              <svg className="animate-spin h-3.5 w-3.5 text-blue-600" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
                <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
              Updating...
            </span>
          )}
        </div>
      </div>

      {!page || page.items.length === 0 ? (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 p-12 text-center shadow-xs">
          <svg className="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
          </svg>
          <p className="mt-3 font-semibold text-slate-800 dark:text-slate-200">{t('orders.no_orders')}</p>
          <p className="text-sm text-slate-400 dark:text-slate-500">{t('orders.no_orders_desc')}</p>
        </div>
      ) : (
        <>
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="min-w-[780px] w-full">
                <thead>
                  <tr className="border-b border-slate-200/90 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/60">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.order')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.customer')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.phone')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.total')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.status')}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.date')}</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.actions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {page.items.map((o) => (
                    <tr key={o.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-slate-500 dark:text-slate-400">#{o.id.slice(0, 8)}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{o.customer_name}</td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{o.customer_phone || '—'}</td>
                      <td className="px-4 py-3 text-sm font-bold text-slate-900 dark:text-slate-100">{o.total_amount.toFixed(2)} TND</td>
                      <td className="px-4 py-3">
                        <Badge variant={BADGE_VARIANTS[o.status] || 'info'}>{o.status.charAt(0).toUpperCase() + o.status.slice(1)}</Badge>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">{new Date(o.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDownloadPdf(o.id)}
                          disabled={downloadingId === o.id}
                          title={t('orders.download_pdf')}
                          className="inline-flex items-center gap-1 text-sm text-emerald-600 hover:text-emerald-800 dark:text-emerald-400 dark:hover:text-emerald-300 font-semibold mr-3 cursor-pointer disabled:opacity-50"
                        >
                          {downloadingId === o.id ? (
                            <svg className="animate-spin h-3.5 w-3.5 text-emerald-600" viewBox="0 0 24 24" fill="none">
                              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
                              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                            </svg>
                          ) : (
                            <span>📄</span>
                          )}
                          <span className="hidden md:inline">{t('orders.download_pdf')}</span>
                        </button>
                        <button onClick={() => openDetail(o.id)} className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold mr-3 cursor-pointer">{t('orders.view')}</button>
                        <button onClick={() => setConfirmDelete(o.id)} className="text-sm text-rose-600 hover:text-rose-800 dark:text-rose-400 dark:hover:text-rose-300 font-semibold cursor-pointer">{t('orders.delete')}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {page.total_pages > 1 && (
              <div className="flex items-center justify-center gap-3 p-4 border-t border-slate-100 dark:border-slate-800">
                <button disabled={pageNum <= 1} onClick={() => setPageNum(pageNum - 1)}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer">{t('common.previous')}</button>
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">{t('common.page')} {pageNum} {t('common.of')} {page.total_pages}</span>
                <button disabled={pageNum >= page.total_pages} onClick={() => setPageNum(pageNum + 1)}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer">{t('common.next')}</button>
              </div>
            )}
          </div>
        </>
      )}

      <ConfirmDialog open={!!confirmDelete} onClose={() => setConfirmDelete(null)} onConfirm={() => handleDelete(confirmDelete!)}
        title={t('orders.delete')} message={t('orders.delete_confirm')} />

      <Modal open={showDetail} onClose={() => setShowDetail(false)}
        title={selectedOrder ? `${t('orders.order')} #${selectedOrder.id.slice(0, 8)}` : t('orders.title')} size="lg">
        {selectedOrder && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 text-sm bg-slate-50/75 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
              <div><span className="text-slate-500 dark:text-slate-400">{t('orders.customer')}:</span> <span className="font-semibold text-slate-900 dark:text-slate-100 ml-2">{selectedOrder.customer_name}</span></div>
              <div><span className="text-slate-500 dark:text-slate-400">{t('orders.phone')}:</span> <span className="font-medium text-slate-900 dark:text-slate-100 ml-2">{selectedOrder.customer_phone || '—'}</span></div>
              <div className="col-span-2"><span className="text-slate-500 dark:text-slate-400">Address:</span> <span className="font-medium text-slate-900 dark:text-slate-100 ml-2">{selectedOrder.customer_address || '—'}</span></div>
              <div><span className="text-slate-500 dark:text-slate-400">{t('orders.status')}:</span> <span className="ml-2"><Badge variant={BADGE_VARIANTS[selectedOrder.status]}>{selectedOrder.status}</Badge></span></div>
              <div><span className="text-slate-500 dark:text-slate-400">{t('orders.total')}:</span> <span className="font-bold text-slate-900 dark:text-slate-100 ml-2">{selectedOrder.total_amount.toFixed(2)} TND</span></div>
              <div><span className="text-slate-500 dark:text-slate-400">{t('orders.date')}:</span> <span className="font-medium text-slate-900 dark:text-slate-100 ml-2">{new Date(selectedOrder.created_at).toLocaleString()}</span></div>
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2.5">{t('orders.items')}</h4>
              <div className="border border-slate-200/90 dark:border-slate-800 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200/90 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/60">
                      <th className="text-left px-3.5 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.product')}</th>
                      <th className="text-right px-3.5 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.qty')}</th>
                      <th className="text-right px-3.5 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.unit')}</th>
                      <th className="text-right px-3.5 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('orders.subtotal')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {selectedOrder.items.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="px-3.5 py-2.5 font-medium text-slate-900 dark:text-slate-100">{item.product_name || (item.product_id ? `${item.product_id.slice(0, 8)}...` : 'Deleted product')}</td>
                        <td className="px-3.5 py-2.5 text-right font-medium">{item.quantity}</td>
                        <td className="px-3.5 py-2.5 text-right text-slate-600 dark:text-slate-400">{item.unit_price.toFixed(2)} TND</td>
                        <td className="px-3.5 py-2.5 text-right font-bold text-slate-900 dark:text-slate-100">{item.subtotal.toFixed(2)} TND</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-600 dark:text-slate-400">{t('orders.change_status')}</span>
                <select value={selectedOrder.status} onChange={(e) => handleStatusChange(selectedOrder.id, e.target.value)}
                  disabled={updatingId === selectedOrder.id}
                  className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 cursor-pointer">
                  {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                </select>
                {updatingId === selectedOrder.id && (
                  <svg className="animate-spin h-4 w-4 text-blue-600" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                )}
              </div>
              <button
                onClick={() => handleDownloadPdf(selectedOrder.id)}
                disabled={downloadingId === selectedOrder.id}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors cursor-pointer disabled:opacity-50"
              >
                {downloadingId === selectedOrder.id ? (
                  <svg className="animate-spin h-4 w-4 text-emerald-600" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                ) : (
                  <span>📄</span>
                )}
                <span>{downloadingId === selectedOrder.id ? t('orders.downloading_pdf') : t('orders.download_pdf')}</span>
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { getAnalytics } from '../api/analytics';
import type { AnalyticsResponse } from '../types';
import { Card, Button } from '../components/ui';

const COLORS = ['#2563eb', '#fb7185', '#10b981', '#f59e0b', '#8b5cf6', '#172554', '#06b6d4', '#64748b'];

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b', confirmed: '#2563eb', preparing: '#8b5cf6', shipped: '#0284c7', delivered: '#10b981', cancelled: '#fb7185',
};

export default function Analytics() {
  const { t } = useTranslation();
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day');
  const [days, setDays] = useState(30);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try { const res = await getAnalytics({ period, days }); setData(res); }
    catch (err) { console.error('Failed to fetch analytics:', err); } finally { setLoading(false); }
  }, [days, period]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="h-16 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 animate-pulse" />
        <div className="grid grid-cols-4 gap-4">{[1,2,3,4].map(i => <div key={i} className="h-24 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 animate-pulse" />)}</div>
        <div className="grid grid-cols-2 gap-6">{[1,2].map(i => <div key={i} className="h-80 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 animate-pulse" />)}</div>
      </div>
    );
  }
  if (!data) return <p className="text-rose-500 font-medium">Failed to load analytics</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('analytics.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('analytics.subtitle')}</p>
        </div>
      </div>

      <Card className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">{t('analytics.period')}:</label>
          <select value={period} onChange={(e) => setPeriod(e.target.value as 'day' | 'week' | 'month')}
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-colors">
            <option value="day">{t('analytics.day')}</option>
            <option value="week">{t('analytics.week')}</option>
            <option value="month">{t('analytics.month')}</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">{t('analytics.range')}:</label>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 transition-colors">
            <option value={7}>7 {t('analytics.day')}s</option>
            <option value={30}>30 {t('analytics.day')}s</option>
            <option value={90}>90 {t('analytics.day')}s</option>
            <option value={365}>1 {t('analytics.day')}</option>
          </select>
        </div>
        <Button size="sm" onClick={fetchData} loading={loading}>{t('analytics.refresh')}</Button>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title={t('analytics.total_revenue')} value={`${data.sales.total_revenue.toLocaleString()} TND`} change={data.sales.revenue_change} />
        <KPICard title={t('analytics.total_orders')} value={data.sales.total_orders} change={data.sales.orders_change} />
        <KPICard title={t('analytics.avg_order_value')} value={`${data.sales.avg_order_value.toLocaleString()} TND`} />
        <KPICard title={t('analytics.conversion_rate')} value={`${data.funnel.conversion_rate}%`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title={t('analytics.revenue_trend')}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.revenue_series}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.7} />
              <XAxis dataKey="date" tickFormatter={(v) => new Date(v).toLocaleDateString()} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis tickFormatter={(v) => `${v.toLocaleString()} TND`} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '0.5rem', color: '#f8fafc', fontSize: '12px' }}
                formatter={(value, name) => name === 'orders' ? [value, 'Orders'] : [`${Number(value ?? 0).toLocaleString()} TND`, 'Revenue']}
              />
              <Line type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#2563eb' }} />
              <Line type="monotone" dataKey="orders" stroke="#fb7185" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#fb7185' }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title={t('analytics.top_products')}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.top_products.slice(0, 8)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.7} />
              <XAxis type="number" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '0.5rem', color: '#f8fafc', fontSize: '12px' }}
                formatter={(value) => [`${Number(value ?? 0).toLocaleString()} TND`, 'Revenue']}
              />
              <Bar dataKey="total_revenue" fill="#2563eb" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title={t('analytics.order_status')}>
          <div className="flex flex-col items-center">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={data.status_distribution} cx="50%" cy="50%" innerRadius={65} outerRadius={100} dataKey="count" nameKey="status"
                  label={({ payload, percent }) => `${(payload as Record<string, string>).status} (${((percent ?? 0) * 100).toFixed(0)}%)`}>
                  {data.status_distribution.map((_, i) => (
                    <Cell key={i} fill={STATUS_COLORS[data.status_distribution[i]?.status] || COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '0.5rem', color: '#f8fafc', fontSize: '12px' }}
                  formatter={(_value, _name, props) => [`${props.payload.count} orders (${props.payload.percentage}%)`, props.payload.status]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="w-full space-y-1 mt-2 text-sm">
              {data.status_distribution.map((s) => (
                <div key={s.status} className="flex items-center gap-2 px-2">
                  <span className="w-3 h-3 rounded-full shrink-0 shadow-xs" style={{ backgroundColor: STATUS_COLORS[s.status] || '#999' }} />
                  <span className="w-24 capitalize text-slate-700 dark:text-slate-200">{s.status}</span>
                  <span className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-300" style={{ width: `${Math.min(s.percentage, 100)}%`, backgroundColor: STATUS_COLORS[s.status] || '#999' }} />
                  </span>
                  <span className="w-16 text-right font-medium text-slate-900 dark:text-slate-100">{s.count}</span>
                  <span className="w-14 text-right text-slate-500 dark:text-slate-400">{s.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
        <ChartCard title={t('analytics.funnel')}>
          <div className="space-y-3">
            <FunnelStep label="Conversations" value={data.funnel.conversations} />
            <FunnelStep label="With Messages" value={data.funnel.conversations_with_messages} parent={data.funnel.conversations} />
            <FunnelStep label="Orders Created" value={data.funnel.orders_created} parent={data.funnel.conversations_with_messages} />
            <FunnelStep label="Completed" value={data.funnel.orders_completed} parent={data.funnel.orders_created} />
            <div className="pt-2 text-center text-sm font-medium text-slate-500 dark:text-slate-400">{t('analytics.conversion_rate')}: <span className="text-blue-600 dark:text-blue-400 font-semibold">{data.funnel.conversion_rate}%</span></div>
          </div>
        </ChartCard>
      </div>

      <ChartCard title={t('analytics.customer_metrics')}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricBox label={t('analytics.total_customers')} value={data.customers.total_customers} />
          <MetricBox label={t('analytics.new')} value={data.customers.new_customers} color="#2563eb" />
          <MetricBox label={t('analytics.returning')} value={data.customers.returning_customers} color="#10b981" />
          <MetricBox label={t('analytics.avg_order_value')} value={`${data.customers.avg_order_value.toLocaleString()} TND`} color="#fb7185" />
        </div>
      </ChartCard>

      <Card>
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-3">{t('analytics.top_products_detail')}</p>
        <div className="overflow-x-auto rounded-lg border border-slate-200/90 dark:border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/60">
              <tr className="border-b border-slate-200 dark:border-slate-700/80 text-left text-slate-600 dark:text-slate-300">
                <th className="p-3 text-xs font-semibold uppercase tracking-wider">{t('orders.product')}</th>
                <th className="p-3 text-right text-xs font-semibold uppercase tracking-wider">{t('analytics.qty_sold')}</th>
                <th className="p-3 text-right text-xs font-semibold uppercase tracking-wider">{t('analytics.revenue')}</th>
                <th className="p-3 text-right text-xs font-semibold uppercase tracking-wider">{t('orders.orders')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {data.top_products.map((p) => (
                <tr key={p.product_id} className="hover:bg-blue-50/30 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 font-medium text-slate-900 dark:text-slate-100">{p.name}</td>
                  <td className="p-3 text-right text-slate-700 dark:text-slate-200">{p.total_quantity}</td>
                  <td className="p-3 text-right font-medium text-slate-900 dark:text-slate-100">{p.total_revenue.toLocaleString()} TND</td>
                  <td className="p-3 text-right text-slate-700 dark:text-slate-200">{p.order_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function KPICard({ title, value, change }: { title: string; value: string | number; change?: number }) {
  return (
    <Card className="hover:border-blue-200 dark:hover:border-slate-700 transition-all duration-200">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{title}</p>
      <p className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mt-1">{value}</p>
      {change !== undefined && (
        <p className={`text-xs mt-1.5 font-medium flex items-center gap-1 ${change >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d={change >= 0 ? 'M7 14l5-5 5 5H7z' : 'M7 10l5 5 5-5H7z'} />
          </svg>
          {change >= 0 ? '+' : ''}{change}% vs last period
        </p>
      )}
    </Card>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card><h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">{title}</h3>{children}</Card>
  );
}

function FunnelStep({ label, value, parent }: { label: string; value: number; parent?: number }) {
  const pct = parent ? Math.round((value / parent) * 100) : 100;
  return (
    <div className="flex items-center gap-3">
      <div className="w-32 text-sm font-medium text-slate-600 dark:text-slate-300">{label}</div>
      <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-lg h-7 relative overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-blue-500 h-full rounded-lg text-white text-xs flex items-center justify-center font-medium shadow-xs transition-all duration-300"
          style={{ width: `${Math.min(pct, 100)}%` }}>{parent ? `${value} (${pct}%)` : value}</div>
      </div>
    </div>
  );
}

function MetricBox({ label, value, color = '#2563eb' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 rounded-xl">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-bold tracking-tight mt-1" style={{ color }}>{value}</p>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { getDashboard, getActivity } from '../api/dashboard';
import type { DashboardData, ActivityItem } from '../api/dashboard';
import { Card } from '../components/ui';
import { useNavigate } from 'react-router-dom';

const statCards = [
  { key: 'total_conversations' as const, tKey: 'dashboard.conversations', color: 'blue', link: '/conversations', icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' },
  { key: 'total_orders' as const, tKey: 'dashboard.orders', color: 'green', link: '/orders', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' },
  { key: 'total_products' as const, tKey: 'dashboard.products', color: 'purple', link: '/products', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
  { key: 'total_stores' as const, tKey: 'dashboard.stores', color: 'indigo', link: '/stores', icon: 'M3 21h18M5 21V7l7-4 7 4v14M9 21v-6a2 2 0 012-2h2a2 2 0 012 2v6' },
  { key: 'total_buyers' as const, tKey: 'dashboard.buyers', color: 'teal', link: '/buyers', icon: 'M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-3-7.6 4 4 0 003 7.6zM17 7a4 4 0 010 7.87' },
  { key: 'total_collections' as const, tKey: 'dashboard.collections', color: 'amber', link: '/collections', icon: 'M4 6h16M4 10h16M4 14h10M4 18h6M8 6v12m8-12v4' },
  { key: 'total_attribute_defs' as const, tKey: 'dashboard.attributes', color: 'slate', link: '/catalog', icon: 'M4 7h16M4 12h10M4 17h13m-6-3l3 3 5-7' },
  { key: 'pending_approvals' as const, tKey: 'dashboard.pending_approvals', color: 'red', link: '/governance', icon: 'M12 6v6l4 2M12 21a9 9 0 100-18 9 9 0 000 18z' },
  { key: 'active_ai_sessions' as const, tKey: 'dashboard.ai_sessions', color: 'cyan', link: '/ai-sessions', icon: 'M9.75 17 9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
];

const colorMap: Record<
  string,
  {
    bg: string;
    text: string;
    ring: string;
    border: string;
    borderHover: string;
    labelHover: string;
    shadowHover: string;
  }
> = {
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-500/10',
    text: 'text-blue-600 dark:text-blue-400',
    ring: 'ring-1 ring-blue-500/20 group-hover:ring-blue-500/40',
    border: 'border-blue-200/80 dark:border-blue-800/50',
    borderHover: 'hover:border-blue-500 dark:hover:border-blue-400',
    labelHover: 'group-hover:text-blue-600 dark:group-hover:text-blue-400',
    shadowHover: 'hover:shadow-blue-500/10',
  },
  green: {
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    text: 'text-emerald-600 dark:text-emerald-400',
    ring: 'ring-1 ring-emerald-500/20 group-hover:ring-emerald-500/40',
    border: 'border-emerald-200/80 dark:border-emerald-800/50',
    borderHover: 'hover:border-emerald-500 dark:hover:border-emerald-400',
    labelHover: 'group-hover:text-emerald-600 dark:group-hover:text-emerald-400',
    shadowHover: 'hover:shadow-emerald-500/10',
  },
  purple: {
    bg: 'bg-purple-50 dark:bg-purple-500/10',
    text: 'text-purple-600 dark:text-purple-400',
    ring: 'ring-1 ring-purple-500/20 group-hover:ring-purple-500/40',
    border: 'border-purple-200/80 dark:border-purple-800/50',
    borderHover: 'hover:border-purple-500 dark:hover:border-purple-400',
    labelHover: 'group-hover:text-purple-600 dark:group-hover:text-purple-400',
    shadowHover: 'hover:shadow-purple-500/10',
  },
  indigo: {
    bg: 'bg-indigo-50 dark:bg-indigo-500/10',
    text: 'text-indigo-600 dark:text-indigo-400',
    ring: 'ring-1 ring-indigo-500/20 group-hover:ring-indigo-500/40',
    border: 'border-indigo-200/80 dark:border-indigo-800/50',
    borderHover: 'hover:border-indigo-500 dark:hover:border-indigo-400',
    labelHover: 'group-hover:text-indigo-600 dark:group-hover:text-indigo-400',
    shadowHover: 'hover:shadow-indigo-500/10',
  },
  teal: {
    bg: 'bg-teal-50 dark:bg-teal-500/10',
    text: 'text-teal-600 dark:text-teal-400',
    ring: 'ring-1 ring-teal-500/20 group-hover:ring-teal-500/40',
    border: 'border-teal-200/80 dark:border-teal-800/50',
    borderHover: 'hover:border-teal-500 dark:hover:border-teal-400',
    labelHover: 'group-hover:text-teal-600 dark:group-hover:text-teal-400',
    shadowHover: 'hover:shadow-teal-500/10',
  },
  amber: {
    bg: 'bg-amber-50 dark:bg-amber-500/10',
    text: 'text-amber-600 dark:text-amber-400',
    ring: 'ring-1 ring-amber-500/20 group-hover:ring-amber-500/40',
    border: 'border-amber-200/80 dark:border-amber-800/50',
    borderHover: 'hover:border-amber-500 dark:hover:border-amber-400',
    labelHover: 'group-hover:text-amber-600 dark:group-hover:text-amber-400',
    shadowHover: 'hover:shadow-amber-500/10',
  },
  slate: {
    bg: 'bg-slate-100 dark:bg-slate-500/10',
    text: 'text-slate-600 dark:text-slate-300',
    ring: 'ring-1 ring-slate-500/20 group-hover:ring-slate-500/40',
    border: 'border-slate-300/80 dark:border-slate-700/80',
    borderHover: 'hover:border-slate-500 dark:hover:border-slate-400',
    labelHover: 'group-hover:text-slate-900 dark:group-hover:text-slate-100',
    shadowHover: 'hover:shadow-slate-500/10',
  },
  red: {
    bg: 'bg-rose-50 dark:bg-rose-500/10',
    text: 'text-rose-600 dark:text-rose-400',
    ring: 'ring-1 ring-rose-500/20 group-hover:ring-rose-500/40',
    border: 'border-rose-200/80 dark:border-rose-800/50',
    borderHover: 'hover:border-rose-500 dark:hover:border-rose-400',
    labelHover: 'group-hover:text-rose-600 dark:group-hover:text-rose-400',
    shadowHover: 'hover:shadow-rose-500/10',
  },
  cyan: {
    bg: 'bg-cyan-50 dark:bg-cyan-500/10',
    text: 'text-cyan-600 dark:text-cyan-400',
    ring: 'ring-1 ring-cyan-500/20 group-hover:ring-cyan-500/40',
    border: 'border-cyan-200/80 dark:border-cyan-800/50',
    borderHover: 'hover:border-cyan-500 dark:hover:border-cyan-400',
    labelHover: 'group-hover:text-cyan-600 dark:group-hover:text-cyan-400',
    shadowHover: 'hover:shadow-cyan-500/10',
  },
};

export default function Dashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loadingActivity, setLoadingActivity] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getDashboard().then(setData).finally(() => setLoading(false));
    getActivity().then((r) => setActivity(r.items)).finally(() => setLoadingActivity(false));
  }, []);

  return (
    <div className="space-y-6">
      {/* Hero Welcome Banner */}
      <div className="bg-gradient-to-r from-[#172554] via-[#1e3a8a] to-[#2563eb] rounded-2xl p-6 sm:p-8 text-white relative overflow-hidden shadow-lg shadow-blue-950/20">
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-[#fb7185]/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute right-40 -top-20 w-72 h-72 bg-blue-400/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold bg-white/10 text-blue-100 border border-white/20 mb-3 backdrop-blur-sm">
            <span className="w-2 h-2 rounded-full bg-[#fb7185] animate-pulse" />
            Social Selling Assistant
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            {t('dashboard.title')}{user?.company_name ? `, ${user?.company_name}` : ''}
          </h1>
          <p className="text-blue-100/90 text-sm sm:text-base mt-1.5 max-w-xl">
            {t('dashboard.subtitle')}
          </p>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((stat) => {
          const c = colorMap[stat.color];
          const value = data?.[stat.key];
          return (
            <button
              key={stat.key}
              onClick={() => navigate(stat.link)}
              className={`group relative text-left w-full p-5 bg-white dark:bg-slate-900 rounded-2xl border ${c.border} ${c.borderHover} shadow-xs ${c.shadowHover} hover:shadow-lg hover:-translate-y-1 transition-all duration-300 ease-out cursor-pointer overflow-hidden`}
            >
              <div className="flex items-center gap-4">
                <div className={`${c.bg} p-3 rounded-xl ${c.ring} group-hover:scale-110 group-hover:rotate-1 transition-all duration-300 ease-out shrink-0`}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`${c.text} transition-colors duration-200`}>
                    <path d={stat.icon} />
                  </svg>
                </div>
                <div className="min-w-0 flex-1">
                  <p className={`text-xs font-semibold text-slate-500 uppercase tracking-wider dark:text-slate-400 ${c.labelHover} transition-colors duration-200 truncate`}>
                    {t(stat.tKey)}
                  </p>
                  {loading ? (
                    <div className="h-7 w-16 bg-slate-200 dark:bg-slate-700 animate-pulse rounded-md mt-1" />
                  ) : (
                    <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight mt-0.5">
                      {value ?? 0}
                    </p>
                  )}
                </div>
              </div>
              <div className="absolute top-3.5 right-3.5 opacity-0 -translate-x-1 translate-y-1 group-hover:opacity-100 group-hover:translate-x-0 group-hover:translate-y-0 transition-all duration-300 ease-out pointer-events-none">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={c.text}>
                  <line x1="7" y1="17" x2="17" y2="7" />
                  <polyline points="7 7 17 7 17 17" />
                </svg>
              </div>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Recent Activity */}
        <Card className="flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('dashboard.recent_activity')}</h3>
            {activity.length > 0 && (
              <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                {activity.length} updates
              </span>
            )}
          </div>
          {loadingActivity ? (
            <div className="space-y-3 flex-1">
              {[1,2,3,4,5].map(i => <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />)}
            </div>
          ) : activity.length === 0 ? (
            <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-8">{t('dashboard.no_activity')}</p>
          ) : (
            <div className="space-y-2.5 flex-1">
              {activity.map((item, i) => {
                const isOrder = item.type === 'order_created';
                const ts = new Date(item.timestamp);
                const now = new Date();
                const diffMs = now.getTime() - ts.getTime();
                const diffMin = Math.floor(diffMs / 60000);
                const descKey = isOrder ? 'dashboard.order_created' : 'dashboard.conversation_started';
                let timeStr: string;
                if (diffMin < 1) timeStr = t('dashboard.just_now');
                else if (diffMin < 60) timeStr = t('dashboard.min_ago', { count: diffMin });
                else if (diffMin < 1440) timeStr = t('dashboard.hour_ago', { count: Math.floor(diffMin / 60) });
                else timeStr = ts.toLocaleDateString();
                return (
                  <div key={i} className="flex items-center gap-3 p-3 bg-slate-50/70 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-800/80">
                    <div className={`w-2 h-2 rounded-full shrink-0 ${isOrder ? 'bg-emerald-500' : 'bg-blue-600'}`} />
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{t(descKey, { name: item.customer_name })}</p>
                    {item.detail && <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded-full">{item.detail}</span>}
                    <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto font-medium shrink-0">{timeStr}</span>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Quick Actions */}
        <Card className="flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('dashboard.quick_actions')}</h3>
            <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500">
              8 shortcuts
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 flex-1">
            {[
              {
                to: '/products',
                titleKey: 'dashboard.add_product',
                descKey: 'dashboard.add_product_desc',
                icon: (
                  <>
                    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                  </>
                ),
                iconBg: 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:bg-blue-600 group-hover:text-white',
                border: 'hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-500/10',
                text: 'group-hover:text-blue-600 dark:group-hover:text-blue-400',
              },
              {
                to: '/conversations',
                titleKey: 'dashboard.new_message',
                descKey: 'dashboard.new_message_desc',
                icon: (
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                ),
                iconBg: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-hover:bg-emerald-600 group-hover:text-white',
                border: 'hover:border-emerald-400 hover:bg-emerald-50/50 dark:hover:bg-emerald-500/10',
                text: 'group-hover:text-emerald-600 dark:group-hover:text-emerald-400',
              },
              {
                to: '/analytics',
                titleKey: 'dashboard.view_analytics',
                descKey: 'dashboard.view_analytics_desc',
                icon: (
                  <>
                    <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
                  </>
                ),
                iconBg: 'bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 group-hover:bg-purple-600 group-hover:text-white',
                border: 'hover:border-purple-400 hover:bg-purple-50/50 dark:hover:bg-purple-500/10',
                text: 'group-hover:text-purple-600 dark:group-hover:text-purple-400',
              },
              {
                to: '/widget',
                titleKey: 'dashboard.widget_settings',
                descKey: 'dashboard.widget_settings_desc',
                icon: (
                  <path d="M12 18h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                ),
                iconBg: 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 group-hover:bg-amber-600 group-hover:text-white',
                border: 'hover:border-amber-400 hover:bg-amber-50/50 dark:hover:bg-amber-500/10',
                text: 'group-hover:text-amber-600 dark:group-hover:text-amber-400',
              },
              {
                to: '/ai-sessions',
                titleKey: 'dashboard.ai_sessions_action',
                descKey: 'dashboard.ai_sessions_desc',
                icon: (
                  <path d="M9.75 17 9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                ),
                iconBg: 'bg-cyan-50 dark:bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 group-hover:bg-cyan-600 group-hover:text-white',
                border: 'hover:border-cyan-400 hover:bg-cyan-50/50 dark:hover:bg-cyan-500/10',
                text: 'group-hover:text-cyan-600 dark:group-hover:text-cyan-400',
              },
              {
                to: '/orders',
                titleKey: 'dashboard.track_orders',
                descKey: 'dashboard.track_orders_desc',
                icon: (
                  <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                ),
                iconBg: 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white',
                border: 'hover:border-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-indigo-500/10',
                text: 'group-hover:text-indigo-600 dark:group-hover:text-indigo-400',
              },
              {
                to: '/seo',
                titleKey: 'dashboard.seo_growth',
                descKey: 'dashboard.seo_growth_desc',
                icon: (
                  <path d="M10 2a8 8 0 107.46 5M14 2h6v6 M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                ),
                iconBg: 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 group-hover:bg-rose-600 group-hover:text-white',
                border: 'hover:border-rose-400 hover:bg-rose-50/50 dark:hover:bg-rose-500/10',
                text: 'group-hover:text-rose-600 dark:group-hover:text-rose-400',
              },
              {
                to: '/governance',
                titleKey: 'dashboard.governance_rules',
                descKey: 'dashboard.governance_rules_desc',
                icon: (
                  <path d="M12 21a9 9 0 110-18 9 9 0 010 18z M12 8v4m0 4h.01" />
                ),
                iconBg: 'bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 group-hover:bg-teal-600 group-hover:text-white',
                border: 'hover:border-teal-400 hover:bg-teal-50/50 dark:hover:bg-teal-500/10',
                text: 'group-hover:text-teal-600 dark:group-hover:text-teal-400',
              },
            ].map((action) => (
              <button
                key={action.to}
                onClick={() => navigate(action.to)}
                className={`p-4 rounded-xl border border-slate-200/90 dark:border-slate-800 ${action.border} transition-all duration-200 text-left cursor-pointer group shadow-2xs hover:shadow-md flex flex-col justify-between`}
              >
                <div>
                  <div className={`w-8 h-8 rounded-lg ${action.iconBg} flex items-center justify-center mb-2.5 transition-colors duration-200`}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      {action.icon}
                    </svg>
                  </div>
                  <p className={`text-sm font-semibold text-slate-900 dark:text-slate-100 ${action.text} transition-colors duration-200`}>
                    {t(action.titleKey)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                    {t(action.descKey)}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

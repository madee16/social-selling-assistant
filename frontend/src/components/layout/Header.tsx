import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useStore } from '../../contexts/StoreContext';
import { useTheme } from '../../contexts/ThemeContext';
import LanguageSwitcher from '../../i18n/LanguageSwitcher';
import { getUnreadCount, listNotifications, markRead, markAllRead, type NotificationItem } from '../../api/notifications';

export default function Header({ onToggleSidebar, sidebarOpen }: { onToggleSidebar: () => void; sidebarOpen: boolean }) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { stores, activeStore, activeStoreId, setActiveStoreId: selectStore, loading: storeLoading } = useStore();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [storeDropdownOpen, setStoreDropdownOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const storeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setDropdownOpen(false);
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (storeRef.current && !storeRef.current.contains(e.target as Node)) setStoreDropdownOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const fetchUnread = async () => {
      try { setUnread((await getUnreadCount()).count); } catch { console.error('Failed to fetch unread count'); }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000);
    return () => clearInterval(interval);
  }, []);

  const openNotifications = async () => {
    setNotifOpen(!notifOpen);
    if (!notifOpen) {
      try {
        const data = await listNotifications();
        setNotifications(data.items);
      } catch { console.error('Failed to fetch notifications'); }
    }
  };

  const handleNotifClick = async (n: NotificationItem) => {
    if (!n.read) {
      await markRead(n.id);
      setUnread((u) => Math.max(0, u - 1));
      setNotifications((prev) => prev.map((x) => (x.id === n.id ? { ...x, read: true } : x)));
    }
    if (n.link) navigate(n.link);
    setNotifOpen(false);
  };

  const handleMarkAllRead = async () => {
    await markAllRead();
    setUnread(0);
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const initials = user?.company_name
    ? user.company_name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
    : 'SC';

  return (
    <header className="bg-white/95 backdrop-blur-md border-b border-slate-200/90 px-4 lg:px-6 py-2.5 flex items-center justify-between sticky top-0 z-20 dark:bg-slate-900/95 dark:border-slate-800">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50/80 transition-all duration-150 dark:text-slate-400 dark:hover:text-blue-400 dark:hover:bg-slate-800 cursor-pointer"
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {sidebarOpen ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 3v18" />
              <path d="m16 15-3-3 3-3" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 3v18" />
              <path d="m14 9 3 3-3 3" />
            </svg>
          )}
        </button>
        <LanguageSwitcher />
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 cursor-pointer"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          ) : (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
            </svg>
          )}
        </button>

        <div className="relative" ref={storeRef}>
          <button onClick={() => setStoreDropdownOpen(!storeDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-all text-sm font-medium text-slate-700 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800 cursor-pointer"
            title={stores.length ? t('header.select_store') : undefined}>
            {!storeLoading && stores.length > 0 && activeStore && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20" />
            )}
            <span className="max-w-[140px] truncate">
              {storeLoading ? t('common.loading') : activeStore ? activeStore.name : stores.length ? t('header.select_store') : t('header.no_store')}
            </span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-400 shrink-0">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {storeDropdownOpen && (
            <div className="absolute left-0 top-full mt-1.5 w-64 bg-white rounded-xl shadow-xl border border-slate-200/90 py-1.5 z-50 dark:bg-slate-800 dark:border-slate-700">
              <div className="px-4 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider dark:text-slate-500">{t('header.stores')}</div>
              {stores.length === 0 ? (
                <div className="px-4 py-3 text-sm text-slate-400 dark:text-slate-500">{t('header.no_stores_hint')}</div>
              ) : (
                stores.map((s) => (
                  <button key={s.id}
                    onClick={() => { selectStore(s.id); setStoreDropdownOpen(false); }}
                    className={`w-full text-left px-4 py-2.5 text-sm flex items-center justify-between hover:bg-slate-50 transition-colors dark:hover:bg-slate-700 cursor-pointer ${s.id === activeStoreId ? 'text-blue-600 bg-blue-50/60 font-medium dark:text-blue-400 dark:bg-blue-500/10' : 'text-slate-700 dark:text-slate-200'}`}>
                    <span className="truncate">{s.name}</span>
                    {s.id === activeStoreId && (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 text-blue-600 dark:text-blue-400">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </button>
                ))
              )}
              <div className="border-t border-slate-100 py-1 mt-1 dark:border-slate-700">
                <button onClick={() => { navigate('/stores'); setStoreDropdownOpen(false); }}
                  className="w-full text-left px-4 py-2.5 text-sm font-medium text-blue-600 hover:bg-blue-50/80 flex items-center gap-2 dark:text-blue-400 dark:hover:bg-blue-500/10 cursor-pointer">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
                  </svg>
                  {t('header.manage_stores')}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="relative" ref={notifRef}>
          <button onClick={openNotifications}
            className="relative p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors dark:hover:bg-slate-800 dark:text-slate-400 cursor-pointer"
            aria-label="View notifications">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" />
            </svg>
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-[#fb7185] text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-xs">
                {unread > 99 ? '99+' : unread}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-80 bg-white rounded-xl shadow-xl border border-slate-200/90 z-50 max-h-96 flex flex-col dark:bg-slate-800 dark:border-slate-700">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700">
                <span className="text-sm font-bold text-slate-900 dark:text-slate-100">Notifications</span>
                {unread > 0 && (
                  <button onClick={handleMarkAllRead} className="text-xs text-blue-600 hover:text-blue-800 font-semibold dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer">
                    Mark all read
                  </button>
                )}
              </div>
              <div className="overflow-y-auto flex-1">
                {notifications.length === 0 ? (
                  <div className="px-4 py-8 text-center text-sm text-slate-400 dark:text-slate-500">No notifications yet</div>
                ) : (
                  notifications.map((n) => (
                    <button key={n.id} onClick={() => handleNotifClick(n)}
                      className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors dark:border-slate-700/50 dark:hover:bg-slate-700 cursor-pointer ${!n.read ? 'bg-blue-50/50 dark:bg-blue-500/10' : ''}`}>
                      <div className="flex items-start gap-2.5">
                        <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${!n.read ? 'bg-blue-600' : 'bg-transparent'}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-slate-900 truncate dark:text-slate-100">{n.title}</p>
                          {n.message && <p className="text-xs text-slate-500 mt-0.5 line-clamp-2 dark:text-slate-400">{n.message}</p>}
                          <p className="text-[10px] text-slate-400 mt-1 dark:text-slate-500">{new Date(n.created_at).toLocaleString()}</p>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="relative" ref={dropdownRef}>
          <button onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-slate-50 transition-colors dark:hover:bg-slate-800 cursor-pointer">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xs font-bold ring-2 ring-blue-500/20 shadow-xs">
              {initials}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-semibold text-slate-700 leading-tight dark:text-slate-200">{user?.company_name || 'User'}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500">{user?.email}</p>
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-400 dark:text-slate-500">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-56 bg-white rounded-xl shadow-xl border border-slate-200/90 py-1.5 z-50 dark:bg-slate-800 dark:border-slate-700">
              <button onClick={() => { navigate('/settings'); setDropdownOpen(false); }}
                className="w-full text-left px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2.5 dark:text-slate-200 dark:hover:bg-slate-700 cursor-pointer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-400">
                  <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                Settings
              </button>
              <div className="border-t border-slate-100 my-1 dark:border-slate-700" />
              <button onClick={logout}
                className="w-full text-left px-4 py-2.5 text-sm font-medium text-rose-600 hover:bg-rose-50 flex items-center gap-2.5 dark:text-rose-400 dark:hover:bg-rose-500/10 cursor-pointer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                {t('auth.logout')}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

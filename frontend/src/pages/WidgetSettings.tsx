import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getWidgetSettings, updateWidgetSettings } from '../api/widget';
import { useToast } from '../contexts/ToastContext';
import type { WidgetSettings } from '../types';
import { Button, Card, Input } from '../components/ui';

export default function WidgetSettingsPage() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<WidgetSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showWhatsApp, setShowWhatsApp] = useState(false);
  const [showMessenger, setShowMessenger] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    getWidgetSettings()
      .then((s) => {
        setSettings(s);
        setShowWhatsApp(!!s.whatsapp_phone_number_id);
        setShowMessenger(!!s.messenger_page_id);
      })
      .catch(() => showToast('error', 'Failed to load widget settings'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await updateWidgetSettings(settings);
      setSettings(updated);
      showToast('success', 'Widget settings saved');
    } catch (err) { console.error('Failed to save widget settings:', err); showToast('error', 'Failed to save settings'); } finally { setSaving(false); }
  };

  const PUBLIC_BASE = (import.meta.env.VITE_PUBLIC_URL || window.location.origin).replace(/\/+$/, '');
  const embedCode = settings?.id ? `<script src="${PUBLIC_BASE}/widget.js" data-widget-id="${settings.id}"></script>` : '';
  const whatsappWebhookUrl = settings?.user_id ? `${PUBLIC_BASE}/api/webhooks/whatsapp?user_id=${settings.user_id}` : '';
  const messengerWebhookUrl = settings?.user_id ? `${PUBLIC_BASE}/api/webhooks/messenger?user_id=${settings.user_id}` : '';

  if (loading) return (
    <div className="max-w-3xl space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-slate-200 dark:bg-slate-700 rounded" /><div className="h-64 bg-slate-100 dark:bg-slate-800 rounded-xl" /><div className="h-32 bg-slate-100 dark:bg-slate-800 rounded-xl" />
    </div>
  );
  if (!settings) return <p className="text-rose-500 font-medium">Failed to load widget settings</p>;

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('widget.title')}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('widget.subtitle')}</p>
        </div>
        <Button onClick={handleSave} loading={saving}>{t('widget.save')}</Button>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">{t('widget.appearance')}</h3>
        <div className="space-y-5">
          <ToggleField label={t('widget.enable')} value={settings.enabled} onChange={(v) => setSettings({ ...settings, enabled: v })} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label={t('widget.title_field')} value={settings.title} onChange={(e) => setSettings({ ...settings, title: e.target.value })} maxLength={100} />
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.primary_color')}</label>
              <div className="flex gap-2">
                <input type="color" value={settings.primary_color} onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })} className="h-9 w-12 rounded-lg border border-slate-300 dark:border-slate-700 cursor-pointer shadow-xs" />
                <input value={settings.primary_color} onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
                  className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" maxLength={7} />
              </div>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.greeting')}</label>
            <textarea value={settings.greeting} onChange={(e) => setSettings({ ...settings, greeting: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" rows={2} maxLength={500} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.position')}</label>
              <select value={settings.position} onChange={(e) => setSettings({ ...settings, position: e.target.value })}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
                <option value="right">{t('widget.bottom_right')}</option>
                <option value="left">{t('widget.bottom_left')}</option>
              </select>
            </div>
            <div className="flex items-end pb-2">
              <ToggleField label={t('widget.show_branding')} value={settings.show_branding} onChange={(v) => setSettings({ ...settings, show_branding: v })} />
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">{t('widget.preview')}</h3>
        <div className="border border-slate-200/90 dark:border-slate-800 rounded-xl p-4 bg-slate-50/70 dark:bg-slate-800/40 relative min-h-[140px]">
          <div className={`fixed bottom-4 ${settings.position === 'right' ? 'right-4' : 'left-4'} flex items-center gap-3 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl p-4 max-w-xs border border-slate-200/90 dark:border-slate-800`}>
            <div className="w-11 h-11 rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0 shadow-md"
              style={{ backgroundColor: settings.primary_color }}>{settings.title.charAt(0).toUpperCase()}</div>
            <div className="flex-1">
              <p className="text-xs font-semibold text-slate-900 dark:text-slate-100">{settings.title}</p>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-0.5">{settings.greeting}</p>
              <input className="mt-2 w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300" placeholder="Type a message..." disabled />
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">{t('widget.embed')}</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{t('widget.embed_desc')}</p>
        <div className="relative">
          <pre className="bg-slate-950 text-emerald-400 p-4 rounded-xl text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-slate-800 shadow-xs">{embedCode || `${t('common.loading')}...`}</pre>
          {embedCode && (
            <button onClick={() => { navigator.clipboard.writeText(embedCode); showToast('success', 'Copied to clipboard'); }}
              className="absolute top-2.5 right-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors">{t('widget.copy')}</button>
          )}
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{t('widget.webhook')}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t('widget.webhook_desc')}</p>
          </div>
        </div>
        <div className="space-y-4">
          <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('widget.user_id')}</h4>
              <button onClick={() => { navigator.clipboard.writeText(settings.user_id); showToast('success', 'Copied to clipboard'); }}
                className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium">{t('widget.copy')}</button>
            </div>
            <pre className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-800 dark:text-slate-200 select-all">{settings.user_id}</pre>
          </div>

          <div className="border border-slate-200/90 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
            <button onClick={() => setShowWhatsApp(!showWhatsApp)}
              className="w-full flex items-center justify-between px-4 py-3 bg-slate-50/80 dark:bg-slate-800/60 hover:bg-slate-100/80 dark:hover:bg-slate-800 transition-colors">
              <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{t('widget.whatsapp')}</span>
              <svg className={`w-4 h-4 text-slate-500 transition-transform dark:text-slate-400 ${showWhatsApp ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showWhatsApp && (
              <div className="p-4 space-y-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-slate-500 dark:text-slate-400">{t('widget.whatsapp_desc')}</p>
                <Input label={t('widget.whatsapp_phone')} value={settings.whatsapp_phone_number_id || ''}
                  onChange={(e) => setSettings({ ...settings, whatsapp_phone_number_id: e.target.value })} placeholder="123456789012345" />
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.whatsapp_token')}</label>
                  <input type="password" value={settings.whatsapp_access_token || ''}
                    onChange={(e) => setSettings({ ...settings, whatsapp_access_token: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.webhook_url')}</label>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{t('widget.webhook_url_desc')}</p>
                  <div className="relative">
                    <pre className="bg-slate-950 text-emerald-400 p-3 rounded-lg text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-slate-800">{whatsappWebhookUrl}</pre>
                    <button onClick={() => { navigator.clipboard.writeText(whatsappWebhookUrl); showToast('success', 'Copied to clipboard'); }}
                      className="absolute top-1.5 right-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2 py-0.5 rounded text-xs transition-colors">{t('widget.copy')}</button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="border border-slate-200/90 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
            <button onClick={() => setShowMessenger(!showMessenger)}
              className="w-full flex items-center justify-between px-4 py-3 bg-slate-50/80 dark:bg-slate-800/60 hover:bg-slate-100/80 dark:hover:bg-slate-800 transition-colors">
              <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{t('widget.messenger')}</span>
              <svg className={`w-4 h-4 text-slate-500 transition-transform dark:text-slate-400 ${showMessenger ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showMessenger && (
              <div className="p-4 space-y-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <p className="text-xs text-slate-500 dark:text-slate-400">{t('widget.messenger_desc')}</p>
                <Input label={t('widget.messenger_page')} value={settings.messenger_page_id || ''}
                  onChange={(e) => setSettings({ ...settings, messenger_page_id: e.target.value })} placeholder="123456789012345" />
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.messenger_token')}</label>
                  <input type="password" value={settings.messenger_access_token || ''}
                    onChange={(e) => setSettings({ ...settings, messenger_access_token: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.webhook_url')}</label>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">{t('widget.webhook_url_desc')}</p>
                  <div className="relative">
                    <pre className="bg-slate-950 text-emerald-400 p-3 rounded-lg text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-slate-800">{messengerWebhookUrl}</pre>
                    <button onClick={() => { navigator.clipboard.writeText(messengerWebhookUrl); showToast('success', 'Copied to clipboard'); }}
                      className="absolute top-1.5 right-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2 py-0.5 rounded text-xs transition-colors">{t('widget.copy')}</button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('widget.verify_token')}</label>
            <div className="relative">
              <pre className="bg-slate-50 dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-800 dark:text-slate-200 select-all">{settings.webhook_verify_token}</pre>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

function ToggleField({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <div className={`relative w-10 h-5 rounded-full transition-colors ${value ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
        <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-xs transition-transform ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
        <input type="checkbox" className="sr-only" checked={value} onChange={(e) => onChange(e.target.checked)} />
      </div>
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors">{label}</span>
    </label>
  );
}

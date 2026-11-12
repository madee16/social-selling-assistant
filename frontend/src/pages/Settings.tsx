import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { updateProfile, changePassword, updatePreferences } from '../api/settings';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button, Card, Input } from '../components/ui';

type Tab = 'profile' | 'password' | 'preferences';

export default function Settings() {
  const { t } = useTranslation();
  const { user, updateUser } = useAuth();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  const [companyName, setCompanyName] = useState(user?.company_name || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [changingPw, setChangingPw] = useState(false);

  const [language, setLanguage] = useState(user?.preferred_language || 'fr');
  const [currency, setCurrency] = useState(user?.currency || 'TND');
  const [notifications, setNotifications] = useState(user?.notifications_enabled ?? true);
  const [aiInstructions, setAiInstructions] = useState(user?.ai_custom_instructions || '');
  const [savingPrefs, setSavingPrefs] = useState(false);

  if (!user) return null;

  const handleProfile = async () => {
    setSavingProfile(true);
    try {
      const updated = await updateProfile({ company_name: companyName, phone: phone || null });
      updateUser(updated);
      showToast('success', 'Profile updated');
    } catch (err) { console.error('Failed to update profile:', err); showToast('error', 'Failed to update profile'); } finally { setSavingProfile(false); }
  };

  const handlePassword = async () => {
    if (newPw !== confirmPw) { showToast('error', 'Passwords do not match'); return; }
    if (newPw.length < 6) { showToast('error', 'Password must be at least 6 characters'); return; }
    setChangingPw(true);
    try {
      await changePassword({ current_password: currentPw, new_password: newPw });
      showToast('success', 'Password changed');
      setCurrentPw(''); setNewPw(''); setConfirmPw('');
    } catch (err) { console.error('Failed to change password:', err); showToast('error', 'Current password is incorrect'); } finally { setChangingPw(false); }
  };

  const handlePreferences = async () => {
    setSavingPrefs(true);
    try {
      const updated = await updatePreferences({
        preferred_language: language,
        currency,
        notifications_enabled: notifications,
        ai_custom_instructions: aiInstructions || null,
      });
      updateUser(updated);
      showToast('success', 'Preferences saved');
    } catch (err) { console.error('Failed to save preferences:', err); showToast('error', 'Failed to save preferences'); } finally { setSavingPrefs(false); }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'profile', label: t('settings.profile') },
    { key: 'password', label: t('settings.password') },
    { key: 'preferences', label: t('settings.preferences') },
  ];

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('settings.title')}</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('settings.subtitle')}</p>
      </div>

      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800">
        {tabs.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab.key ? 'border-blue-600 text-blue-600 dark:text-blue-400 font-semibold' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      {activeTab === 'profile' && (
        <Card>
          <div className="space-y-4">
            <Input label={t('settings.company_name')} value={companyName} onChange={(e) => setCompanyName(e.target.value)} maxLength={255} />
            <Input label={t('auth.email')} value={user.email} disabled />
            <Input label={t('orders.phone')} value={phone || ''} onChange={(e) => setPhone(e.target.value)} maxLength={50} />
            <div className="flex justify-end pt-2">
              <Button onClick={handleProfile} loading={savingProfile}>{t('common.save')}</Button>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'password' && (
        <Card>
          <div className="space-y-4">
            <Input label={t('settings.current_password')} type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} />
            <Input label={t('settings.new_password')} type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} maxLength={128} />
            <Input label={t('settings.confirm_password')} type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} />
            <div className="flex justify-end pt-2">
              <Button onClick={handlePassword} loading={changingPw} disabled={!currentPw || !newPw || !confirmPw}>{t('settings.change_password')}</Button>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'preferences' && (
        <Card>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('settings.language')}</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
                <option value="fr">Français</option>
                <option value="en">English</option>
                <option value="ar">العربية</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('settings.currency')}</label>
              <select value={currency} onChange={(e) => setCurrency(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600">
                <option value="TND">TND (د.ت)</option>
                <option value="EUR">EUR (€)</option>
                <option value="USD">USD ($)</option>
              </select>
            </div>
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className={`relative w-10 h-5 rounded-full transition-colors ${notifications ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-xs transition-transform ${notifications ? 'translate-x-5' : 'translate-x-0.5'}`} />
                <input type="checkbox" className="sr-only" checked={notifications} onChange={(e) => setNotifications(e.target.checked)} />
              </div>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-slate-100 transition-colors">{t('settings.notifications')}</span>
            </label>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">{t('settings.ai_instructions')}</label>
              <textarea value={aiInstructions} onChange={(e) => setAiInstructions(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600" rows={4} maxLength={5000} placeholder={t('settings.ai_placeholder')} />
            </div>
            <div className="flex justify-end pt-2">
              <Button onClick={handlePreferences} loading={savingPrefs}>{t('common.save')}</Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

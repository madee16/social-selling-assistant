import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card, Input } from '../components/ui';
import client from '../api/client';

export default function ResetPassword() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (password !== confirm) { setError(t('auth.passwords_mismatch')); return; }
    if (password.length < 6) { setError(t('auth.password_min')); return; }
    setLoading(true);
    setError('');
    try {
      await client.post('/api/auth/reset-password', { token, new_password: password });
      navigate('/login');
    } catch (err) {
      console.error('Reset password failed:', err);
      setError(t('auth.reset_failed'));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc] px-4 dark:bg-[#0b1120] relative overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <Card className="max-w-md w-full text-center p-8 rounded-2xl shadow-xl relative z-10 border-slate-200/90 dark:border-slate-800">
          <h2 className="text-xl font-bold tracking-tight text-slate-900 mb-2 dark:text-slate-100">{t('auth.invalid_link')}</h2>
          <Link to="/forgot-password" className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium inline-flex items-center gap-1">← {t('auth.request_new')}</Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f8fafc] px-4 dark:bg-[#0b1120] relative overflow-hidden">
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

      <Card className="max-w-md w-full p-8 rounded-2xl shadow-xl relative z-10 border-slate-200/90 dark:border-slate-800">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-navy-900 text-white font-bold text-xl shadow-md mb-3 relative">
            S
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-rose-500 rounded-full border-2 border-white dark:border-slate-900" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('auth.reset_title')}</h1>
          <p className="text-sm text-slate-500 mt-1 dark:text-slate-400">{t('auth.reset_subtitle')}</p>
        </div>
        <div className="space-y-4">
          <Input label={t('auth.new_password')} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Input label={t('auth.confirm_password')} type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          {error && <p className="text-sm text-rose-600 font-medium">{error}</p>}
          <Button onClick={handleSubmit} loading={loading} disabled={!password || !confirm} className="w-full">{t('auth.reset_button')}</Button>
        </div>
      </Card>
    </div>
  );
}

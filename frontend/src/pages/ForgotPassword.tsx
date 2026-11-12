import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Button, Card, Input } from '../components/ui';
import client from '../api/client';

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      await client.post('/api/auth/forgot-password', { email });
      setSubmitted(true);
    } catch (err) {
      console.error('Forgot password failed:', err);
      setError(t('auth.error_occurred'));
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc] px-4 dark:bg-[#0b1120] relative overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <Card className="max-w-md w-full text-center p-8 rounded-2xl shadow-xl relative z-10 border-slate-200/90 dark:border-slate-800">
          <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4 dark:bg-emerald-500/20 shadow-xs">
            <svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 mb-2 dark:text-slate-100">{t('auth.check_email')}</h2>
          <p className="text-sm text-slate-500 mb-6 dark:text-slate-400">{t('auth.reset_sent')}</p>
          <Link to="/login" className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium inline-flex items-center gap-1">← {t('auth.back_to_login')}</Link>
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
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('auth.forgot_title')}</h1>
          <p className="text-sm text-slate-500 mt-1 dark:text-slate-400">{t('auth.forgot_subtitle')}</p>
        </div>
        <div className="space-y-4">
          <Input label={t('auth.email')} type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
          {error && <p className="text-sm text-rose-600 font-medium">{error}</p>}
          <Button onClick={handleSubmit} loading={loading} disabled={!email.trim()} className="w-full">{t('auth.send_reset')}</Button>
        </div>
        <div className="mt-5 text-center">
          <Link to="/login" className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium">{t('auth.back_to_login')}</Link>
        </div>
      </Card>
    </div>
  );
}

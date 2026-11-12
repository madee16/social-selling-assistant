import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../api/auth';
import { useAuth } from '../contexts/AuthContext';
import { Button, Input } from '../components/ui';

export default function Register() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [phone, setPhone] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) { setError('Passwords do not match'); return; }
    if (password.length < 6) { setError('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      const res = await register(email, password, companyName, phone || undefined);
      setAuth(res.access_token);
      navigate('/dashboard');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string; code?: string };
      if (axiosErr.response?.data?.detail) setError(axiosErr.response.data.detail);
      else if (axiosErr.code === 'ERR_NETWORK') setError('Cannot reach the server. Make sure the backend is running.');
      else setError(axiosErr.message || 'Registration failed');
    } finally { setLoading(false); }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#f8fafc] dark:bg-[#0b1120] p-4 relative overflow-hidden">
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-navy-900 text-white font-bold text-xl shadow-md mb-3 relative">
            S
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-rose-500 rounded-full border-2 border-white dark:border-slate-900" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">{t('app.name')}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('auth.create_account_title')}</p>
        </div>
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200/90 p-8 dark:bg-slate-900 dark:border-slate-800">
          {error && <div className="mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-sm font-medium text-rose-700 dark:bg-rose-950/30 dark:border-rose-800/60 dark:text-rose-400">{error}</div>}
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label={t('auth.company_name')} value={companyName} onChange={(e) => setCompanyName(e.target.value)} required placeholder={t('auth.company_name')} />
            <Input label={t('auth.email')} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@company.com" />
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5 dark:text-slate-300">{t('auth.password')}</label>
              <div className="relative">
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} required placeholder={t('auth.password')}
                  className="block w-full rounded-lg border border-slate-300 bg-white pl-10 pr-10 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/25 focus:border-blue-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100 dark:placeholder-slate-500 transition-colors" />
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0110 0v4" /></svg>
                </div>
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" /><line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
                  )}
                </button>
              </div>
            </div>
            <Input label={t('auth.confirm_password')} type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required placeholder={t('auth.confirm_password')} />
            <Input label={`${t('auth.phone')} (${t('chat.optional')})`} type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+216 XX XXX XXX" />
            <Button type="submit" loading={loading} className="w-full mt-2">{t('auth.create_account')}</Button>
          </form>
        </div>
        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
          {t('auth.has_account')}{' '}
          <Link to="/login" className="font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">{t('auth.sign_in_link')}</Link>
        </p>
      </div>
    </div>
  );
}

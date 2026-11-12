import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-[65vh]">
      <div className="text-center max-w-md p-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400 mb-6 shadow-xs">
          <span className="font-extrabold text-2xl tracking-tight">404</span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 mb-2 dark:text-slate-100">Page not found</h2>
        <p className="text-sm text-slate-500 mb-6 dark:text-slate-400">The page you're looking for doesn't exist or has been moved.</p>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 shadow-xs hover:shadow-sm active:scale-[0.98] transition-all"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}

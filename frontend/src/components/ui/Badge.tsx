import { type ReactNode } from 'react';

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'indigo' | 'coral' | 'accent' | 'cobalt';
  children: ReactNode;
  className?: string;
  size?: 'sm' | 'md';
}

const colors: Record<string, string> = {
  default: 'bg-slate-100 text-slate-700 ring-1 ring-slate-600/10 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-500/30',
  success: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30',
  warning: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30',
  danger: 'bg-red-50 text-red-700 ring-1 ring-red-600/20 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/30',
  info: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-500/30',
  cobalt: 'bg-blue-50 text-blue-700 ring-1 ring-blue-600/20 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-500/30',
  coral: 'bg-rose-50 text-rose-700 ring-1 ring-rose-500/25 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-500/30',
  accent: 'bg-rose-50 text-rose-700 ring-1 ring-rose-500/25 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-500/30',
  purple: 'bg-purple-50 text-purple-700 ring-1 ring-purple-600/20 dark:bg-purple-500/15 dark:text-purple-300 dark:ring-purple-500/30',
  indigo: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600/20 dark:bg-indigo-500/15 dark:text-indigo-300 dark:ring-indigo-500/30',
};

const statusMap: Record<string, string> = {
  pending: 'warning',
  confirmed: 'info',
  preparing: 'purple',
  shipped: 'indigo',
  delivered: 'success',
  cancelled: 'danger',
  active: 'success',
  closed: 'default',
  escalated: 'coral',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-[11px]',
  md: 'px-2.5 py-0.5 text-xs',
};

export default function Badge({ variant = 'default', children, className = '', size = 'md' }: BadgeProps) {
  const isStr = typeof children === 'string';
  const resolved = (isStr && statusMap[children.toLowerCase()]) ? statusMap[children.toLowerCase()] : variant;
  const colorClass = colors[resolved] || colors.default;

  return (
    <span className={`inline-flex items-center font-medium rounded-full capitalize ${colorClass} ${sizeStyles[size]} ${className}`}>
      {children}
    </span>
  );
}

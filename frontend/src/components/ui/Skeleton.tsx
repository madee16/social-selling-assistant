export default function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/90 overflow-hidden dark:bg-slate-900 dark:border-slate-800">
      <div className="border-b border-slate-100 p-4 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="border-b border-slate-100/70 p-4 last:border-0 dark:border-slate-800/50">
          <div className="flex gap-4">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4 flex-1" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-6 space-y-4 dark:bg-slate-900 dark:border-slate-800">
      <Skeleton className="h-5 w-1/3" />
      <Skeleton className="h-8 w-1/4" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

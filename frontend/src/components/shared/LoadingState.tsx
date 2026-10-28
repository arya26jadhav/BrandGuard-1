import { cn } from "@/lib/utils";

type LoadingStateProps = { rows?: number; className?: string; label?: string };
export function LoadingState({ rows = 4, className, label = "Loading content" }: LoadingStateProps) {
  return <div className={cn("surface-card space-y-3 p-4", className)} role="status" aria-label={label} aria-busy="true"><span className="sr-only">{label}</span><div className="h-4 w-40 animate-pulse rounded bg-slate-100" /><div className="h-3 w-64 max-w-full animate-pulse rounded bg-slate-100" />{Array.from({ length: rows }, (_, index) => <div key={index} className="flex items-center gap-3 border-t border-slate-100 pt-3"><div className="h-8 w-8 animate-pulse rounded-md bg-slate-100" /><div className="flex-1 space-y-2"><div className="h-3 w-2/5 animate-pulse rounded bg-slate-100" /><div className="h-2.5 w-3/5 animate-pulse rounded bg-slate-100" /></div><div className="h-6 w-16 animate-pulse rounded-full bg-slate-100" /></div>)}</div>;
}

import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

type ErrorStateProps = { title?: string; description?: string; onRetry?: () => void; className?: string };
export function ErrorState({ title = "We couldn't load this page", description = "Check your connection and try again. Your work has not been changed.", onRetry, className }: ErrorStateProps) {
  return <div role="alert" className={cn("flex min-h-48 flex-col items-center justify-center rounded-xl border border-red-100 bg-white px-5 py-7 text-center", className)}><div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-red-50 text-red-700"><AlertTriangle size={19} aria-hidden="true" /></div><h3 className="text-[14px] font-semibold text-navy">{title}</h3><p className="mt-1.5 max-w-sm text-[12px] leading-5 text-muted-foreground">{description}</p>{onRetry && <button type="button" onClick={onRetry} className="focus-ring mt-3 inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-[12px] font-semibold text-slate-700 hover:bg-slate-50"><RefreshCw size={13} aria-hidden="true" />Try again</button>}</div>;
}

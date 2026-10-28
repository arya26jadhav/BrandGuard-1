import type { ReactNode } from "react";
import { FileSearch, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

type EmptyStateProps = { title: string; description: string; actionLabel?: string; onAction?: () => void; icon?: ReactNode; className?: string };
export function EmptyState({ title, description, actionLabel, onAction, icon, className }: EmptyStateProps) {
  return <div className={cn("flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-5 py-7 text-center", className)}><div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-brand">{icon ?? <FileSearch size={19} aria-hidden="true" />}</div><h3 className="text-[14px] font-semibold text-navy">{title}</h3><p className="mt-1.5 max-w-sm text-[12px] leading-5 text-muted-foreground">{description}</p>{actionLabel && onAction && <button type="button" onClick={onAction} className="focus-ring mt-3 inline-flex h-9 items-center gap-2 rounded-md bg-brand px-3 text-[12px] font-semibold text-white transition hover:bg-blue-700"><Plus size={14} aria-hidden="true" />{actionLabel}</button>}</div>;
}

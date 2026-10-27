import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type PageHeaderProps = { title: string; description?: string; eyebrow?: string; actions?: ReactNode; className?: string };
export function PageHeader({ title, description, eyebrow, actions, className }: PageHeaderProps) {
  return <header className={cn("mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-center", className)}>
    <div className="min-w-0">{eyebrow && <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-brand">{eyebrow}</p>}<h1 className="text-[18px] font-semibold leading-6 tracking-tight text-navy">{title}</h1>{description && <p className="mt-1 max-w-2xl text-[12px] leading-4 text-muted-foreground">{description}</p>}</div>
    {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
  </header>;
}

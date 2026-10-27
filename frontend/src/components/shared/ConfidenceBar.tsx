import { cn } from "@/lib/utils";

type ConfidenceBarProps = { value: number; label?: string; className?: string; showLabel?: boolean };
export function ConfidenceBar({ value, label = "Confidence", className, showLabel = true }: ConfidenceBarProps) {
  const safeValue = Math.max(0, Math.min(100, Math.round(value <= 1 ? value * 100 : value)));
  return <div className={cn("w-full", className)}>{showLabel && <div className="mb-1 flex items-center justify-between gap-2 text-[12px]"><span className="text-muted-foreground">{label}</span><span className="font-semibold tabular-nums text-slate-700">{safeValue}%</span></div>}<div className="h-1.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={safeValue}><div className="h-full rounded-full bg-brand transition-[width]" style={{ width: `${safeValue}%` }} /></div></div>;
}

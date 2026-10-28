import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import type { Finding } from "@/types";
import { cn } from "@/lib/utils";

type SeverityBadgeProps = { severity: Finding["severity"]; className?: string; showIcon?: boolean };
const config = {
  critical: { label: "Critical", icon: AlertCircle, className: "border-red-200 bg-critical-soft text-critical" },
  warning: { label: "Warning", icon: AlertTriangle, className: "border-amber-200 bg-warning-soft text-warning" },
  info: { label: "Info", icon: Info, className: "border-blue-200 bg-info-soft text-info" },
};
export function SeverityBadge({ severity, className, showIcon = true }: SeverityBadgeProps) {
  const item = config[severity]; const Icon = item.icon;
  return <span className={cn("inline-flex h-6 items-center gap-1 rounded-full border px-2 text-[11px] font-semibold leading-none", item.className, className)}>{showIcon && <Icon aria-hidden="true" size={12} strokeWidth={2.2} />}<span>{item.label}</span></span>;
}

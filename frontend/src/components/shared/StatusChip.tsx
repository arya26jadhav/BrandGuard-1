import { CheckCircle2, FileCheck2, FileText, GitPullRequest, Globe2, RefreshCw, RotateCcw, Wrench } from "lucide-react";
import type { ContentStatus } from "@/types";
import { cn } from "@/lib/utils";

type StatusChipProps = { status: ContentStatus; className?: string };
const config: Record<ContentStatus, { className: string; icon: typeof FileText }> = {
  Draft: { className: "border-slate-200 bg-slate-100 text-slate-700", icon: FileText },
  Checked: { className: "border-blue-200 bg-blue-50 text-blue-700", icon: CheckCircle2 },
  Fixing: { className: "border-amber-200 bg-amber-50 text-amber-800", icon: Wrench },
  "In Review": { className: "border-purple-200 bg-purple-50 text-purple-800", icon: GitPullRequest },
  "Changes requested": { className: "border-orange-200 bg-orange-50 text-orange-800", icon: RotateCcw },
  Approved: { className: "border-green-200 bg-green-50 text-green-800", icon: FileCheck2 },
  Published: { className: "border-emerald-800 bg-emerald-800 text-white", icon: Globe2 },
  "Needs revalidation": { className: "border-red-300 bg-white text-red-700", icon: RefreshCw },
};
export function StatusChip({ status, className }: StatusChipProps) {
  const item = config[status]; const Icon = item.icon;
  return <span className={cn("inline-flex h-6 items-center gap-1 whitespace-nowrap rounded-full border px-2 text-[11px] font-semibold", item.className, className)}><Icon aria-hidden="true" size={11} strokeWidth={2.2} />{status}</span>;
}

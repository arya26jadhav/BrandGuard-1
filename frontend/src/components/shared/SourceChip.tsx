import { BookOpen, ExternalLink, FileText, Image as ImageIcon, ShieldCheck } from "lucide-react";
import type { BrandSource } from "@/types";
import { cn } from "@/lib/utils";

type SourceChipProps = { sourceId: string; version?: number; category?: BrandSource["category"]; onClick?: () => void; className?: string };
const icons = { Guideline: BookOpen, "Product fact": ShieldCheck, Disclaimer: FileText, Asset: ImageIcon };
export function SourceChip({ sourceId, version, category = "Guideline", onClick, className }: SourceChipProps) {
  const Icon = icons[category];
  const content = <><Icon aria-hidden="true" size={12} /><span>{sourceId}{version !== undefined ? ` · v${version}` : ""}</span>{onClick && <ExternalLink aria-hidden="true" size={10} />}</>;
  const styles = cn("inline-flex h-6 max-w-full items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2 text-[11px] font-medium text-slate-700", onClick && "cursor-pointer hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800 focus-ring", className);
  return onClick ? <button type="button" onClick={onClick} className={styles} aria-label={`Open source ${sourceId}${version !== undefined ? ` version ${version}` : ""}`}>{content}</button> : <span className={styles}>{content}</span>;
}

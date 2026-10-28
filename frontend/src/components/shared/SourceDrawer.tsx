
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Clipboard,
  Clock3,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Pencil,
  ShieldCheck,
  X,
} from "lucide-react";
import type { BrandSource } from "@/types";
import { listSources } from "@/api/sources";
import { cn } from "@/lib/utils";

type SourceDrawerProps = {
  source: BrandSource | null;
  sourceId?: string;
  onClose: () => void;
  onCopy?: (sourceId: string) => void;
  onEdit?: (source: BrandSource) => void;
  isAdmin?: boolean;
  loading?: boolean;
};

const sourceIcons = {
  Guideline: BookOpen,
  "Product fact": ShieldCheck,
  Disclaimer: FileText,
  Asset: ImageIcon,
};

const contentItemsBySource: Record<
  string,
  { id: string; title: string; channel: string }[]
> = {
  "GUIDE-001": [
    { id: "GG-101", title: "Summer Glow launch post", channel: "Instagram" },
    { id: "GG-104", title: "Tea Tree product page", channel: "Website" },
    { id: "GG-109", title: "October skincare newsletter", channel: "Email" },
    { id: "GG-112", title: "Daily skincare campaign", channel: "Paid ad" },
  ],
  "GUIDE-022": [
    { id: "GG-102", title: "Sunscreen product promotion", channel: "Instagram" },
    { id: "GG-106", title: "Face wash campaign", channel: "Paid ad" },
    { id: "GG-109", title: "October skincare newsletter", channel: "Email" },
    { id: "GG-114", title: "Product benefits page", channel: "Website" },
  ],
  "FACT-009": [
    { id: "GG-104", title: "Tea Tree product page", channel: "Website" },
    { id: "GG-106", title: "Face wash campaign", channel: "Paid ad" },
    { id: "GG-111", title: "Tea Tree social post", channel: "Instagram" },
    { id: "GG-114", title: "Product benefits page", channel: "Website" },
  ],
  "FACT-014": [
    { id: "GG-101", title: "Summer Glow launch post", channel: "Instagram" },
    { id: "GG-106", title: "Face wash campaign", channel: "Paid ad" },
    { id: "GG-111", title: "Tea Tree social post", channel: "Instagram" },
    { id: "GG-114", title: "Product benefits page", channel: "Website" },
  ],
  "FACT-027": [
    { id: "GG-102", title: "Sunscreen product promotion", channel: "Instagram" },
    { id: "GG-108", title: "Sunscreen product page", channel: "Website" },
    { id: "GG-110", title: "Festive skincare offer", channel: "Paid ad" },
    { id: "GG-115", title: "Sunscreen email campaign", channel: "Email" },
  ],
  "ASSET-001": [
    { id: "GG-101", title: "Summer Glow launch post", channel: "Instagram" },
    { id: "GG-107", title: "Brand introduction", channel: "Website" },
    { id: "GG-110", title: "Festive skincare offer", channel: "Paid ad" },
    { id: "GG-113", title: "Brand newsletter", channel: "Email" },
  ],
  "GUIDE-031": [
    { id: "GG-103", title: "Sunscreen visual ad", channel: "Paid ad" },
    { id: "GG-105", title: "Summer skincare graphic", channel: "Instagram" },
    { id: "GG-108", title: "Sunscreen product page", channel: "Website" },
    { id: "GG-112", title: "Daily skincare campaign", channel: "Paid ad" },
  ],
};

function getExpiryState(expiryDate?: string) {
  if (!expiryDate) return "none" as const;

  const parsed = new Date(expiryDate);
  if (Number.isNaN(parsed.getTime())) return "none" as const;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  parsed.setHours(0, 0, 0, 0);

  const days = Math.ceil(
    (parsed.getTime() - today.getTime()) / 86_400_000,
  );

  if (days < 0) return "expired" as const;
  if (days < 30) return "soon" as const;
  return "valid" as const;
}

function formatExpiry(expiryDate?: string) {
  if (!expiryDate) return "No expiry set";

  const parsed = new Date(expiryDate);
  if (Number.isNaN(parsed.getTime())) return expiryDate;

  return parsed.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function InitialsAvatar({ name }: { name: string }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <span
      aria-label={name}
      title={name}
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-bold text-blue-800"
    >
      {initials || "?"}
    </span>
  );
}

function SourceSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading source details"
      className="space-y-5 px-4 py-4"
    >
      <span className="sr-only">Loading source details...</span>

      <div className="rounded-lg border border-slate-100 p-3">
        <div className="h-3 w-28 animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-4 w-full animate-pulse rounded bg-slate-100" />
        <div className="mt-2 h-4 w-4/5 animate-pulse rounded bg-slate-100" />
        <div className="mt-2 h-4 w-2/3 animate-pulse rounded bg-slate-100" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="rounded-lg border border-slate-100 p-3">
            <div className="h-3 w-16 animate-pulse rounded bg-slate-200" />
            <div className="mt-3 h-4 w-24 animate-pulse rounded bg-slate-100" />
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />
        {[1, 2, 3].map((item) => (
          <div
            key={item}
            className="h-12 animate-pulse rounded-lg bg-slate-100"
          />
        ))}
      </div>
    </div>
  );
}

export default function SourceDrawer({
  source: sourceProp,
  sourceId,
  onClose,
  onCopy,
  onEdit,
  isAdmin = false,
  loading = false,
}: SourceDrawerProps) {
  const [copied, setCopied] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [copyError, setCopyError] = useState(false);

  const [fetchedSource, setFetchedSource] = useState<BrandSource | null>(null);

  useEffect(() => {
    if (sourceProp || !sourceId) {
      setFetchedSource(null);
      return;
    }
    let cancelled = false;
    listSources()
      .then((sources) => {
        if (!cancelled) setFetchedSource(sources.find((item) => item.id === sourceId) ?? null);
      })
      .catch(() => {
        if (!cancelled) setFetchedSource(null);
      });
    return () => {
      cancelled = true;
    };
  }, [sourceProp, sourceId]);

  const currentSource = sourceProp ?? fetchedSource;

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!sourceProp && !sourceId && !loading) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleClose();
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [sourceProp, sourceId, loading, handleClose]);

  useEffect(() => {
    setCopied(false);
    setCopyError(false);
    setHistoryOpen(true);
  }, [currentSource?.id]);

  const handleCopy = async () => {
    if (!currentSource) return;

    try {
      await navigator.clipboard.writeText(currentSource.id);
      setCopied(true);
      setCopyError(false);
      onCopy?.(currentSource.id);
    } catch {
      setCopyError(true);
      setCopied(false);
    }
  };

  if (!currentSource && !loading && !sourceId) {
    return null;
  }

  const source = currentSource;
  const Icon = source
    ? sourceIcons[source.category as keyof typeof sourceIcons] ?? FileText
    : FileText;

  const history = source?.versionHistory ?? [];
  const expiryState = getExpiryState(source?.expiryDate);
  const usedItems = source ? contentItemsBySource[source.id] ?? [] : [];

  return (
    <div className="fixed inset-0 z-[80] flex justify-end" role="presentation">
      <button
        type="button"
        aria-label="Close source details"
        className="absolute inset-0 cursor-default bg-slate-950/35"
        onClick={handleClose}
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-drawer-title"
        className="relative flex h-full w-full max-w-[420px] flex-col border-l border-[#E3E8F2] bg-white shadow-2xl"
      >
        <header className="flex min-h-[68px] items-center justify-between gap-3 border-b border-[#E3E8F2] px-4 py-3">
          {loading ? (
            <div className="flex flex-1 items-center gap-3">
              <div className="h-9 w-9 animate-pulse rounded-lg bg-slate-100" />
              <div className="flex-1">
                <div className="h-4 w-36 animate-pulse rounded bg-slate-200" />
                <div className="mt-2 h-3 w-20 animate-pulse rounded bg-slate-100" />
              </div>
            </div>
          ) : source ? (
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-blue-100 bg-blue-50 text-[#2F5BEA]">
                <Icon size={18} />
              </div>

              <div className="min-w-0">
                <h2
                  id="source-drawer-title"
                  className="truncate text-[16px] font-semibold leading-5 text-[#14213D]"
                >
                  {source.title}
                </h2>

                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                  <span className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-slate-700">
                    {source.id}
                  </span>

                  <span
                    className={cn(
                      "inline-flex h-5 items-center gap-1 rounded-full px-2 text-[10px] font-semibold",
                      source.status === "Active"
                        ? "bg-emerald-50 text-emerald-800"
                        : "bg-amber-50 text-amber-900",
                    )}
                  >
                    {source.status === "Active" ? (
                      <Check size={11} />
                    ) : (
                      <AlertCircle size={11} />
                    )}
                    {source.status}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div>
              <h2
                id="source-drawer-title"
                className="text-[16px] font-semibold text-[#14213D]"
              >
                Source not found
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                This source may have been removed.
              </p>
            </div>
          )}

          <button
            type="button"
            onClick={handleClose}
            aria-label="Close source drawer"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2F5BEA]"
          >
            <X size={18} />
          </button>
        </header>

        {loading ? (
          <div className="flex-1 overflow-y-auto">
            <SourceSkeleton />
          </div>
        ) : !source ? (
          <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-800">
              <FileText size={22} />
            </div>

            <h3 className="mt-4 text-[15px] font-semibold text-[#14213D]">
              Source not found
            </h3>

            <p className="mt-2 max-w-[270px] text-[13px] leading-5 text-slate-600">
              We couldn't find the approved rule for this source ID. Close this
              panel and check the source chip again.
            </p>

            {sourceId && (
              <span className="mt-3 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-mono text-xs text-slate-700">
                {sourceId}
              </span>
            )}

            <button
              type="button"
              onClick={handleClose}
              className="mt-5 h-9 rounded-lg bg-[#2F5BEA] px-4 text-[13px] font-semibold text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
              <p className="text-[13px] leading-5 text-slate-600">
                This is the approved rule behind the flag.
              </p>

              <section aria-labelledby="approved-text-heading">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3
                    id="approved-text-heading"
                    className="text-[12px] font-semibold text-slate-700"
                  >
                    Approved text
                  </h3>
                  <span className="text-[11px] text-slate-500">
                    Version {source.version}
                  </span>
                </div>

                <blockquote className="rounded-lg border border-blue-100 bg-[#EFF5FF] px-3 py-3 text-[13px] leading-5 text-slate-800">
                  {source.excerpt}
                </blockquote>

                <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-4 text-slate-500">
                  <ShieldCheck
                    size={13}
                    className="mt-0.5 shrink-0 text-blue-700"
                  />
                  This wording is approved for use according to the source
                  record.
                </p>
              </section>

              <section aria-labelledby="source-details-heading">
                <h3
                  id="source-details-heading"
                  className="mb-2.5 text-[12px] font-semibold text-slate-700"
                >
                  Source details
                </h3>

                <div className="grid grid-cols-2 gap-2">
                  <div className="min-w-0 rounded-lg border border-[#E3E8F2] p-2.5">
                    <span className="text-[11px] text-slate-500">Owner</span>
                    <div className="mt-1.5 flex min-w-0 items-center gap-2">
                      <InitialsAvatar name={source.owner || "Unknown"} />
                      <span className="truncate text-[12px] font-medium text-slate-800">
                        {source.owner || "Unknown"}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-lg border border-[#E3E8F2] p-2.5">
                    <span className="text-[11px] text-slate-500">Version</span>
                    <p className="mt-2 text-[13px] font-semibold text-slate-800">
                      v{source.version}
                    </p>
                  </div>

                  <div className="rounded-lg border border-[#E3E8F2] p-2.5">
                    <span className="text-[11px] text-slate-500">Last updated</span>
                    <p className="mt-2 flex items-center gap-1.5 text-[12px] font-medium text-slate-800">
                      <Clock3 size={13} className="shrink-0 text-slate-400" />
                      {source.updatedAt}
                    </p>
                  </div>

                  <div
                    className={cn(
                      "rounded-lg border p-2.5",
                      expiryState === "expired"
                        ? "border-red-200 bg-red-50"
                        : expiryState === "soon"
                          ? "border-amber-200 bg-amber-50"
                          : "border-[#E3E8F2]",
                    )}
                  >
                    <span className="text-[11px] text-slate-500">Expires</span>
                    <p
                      className={cn(
                        "mt-2 flex items-center gap-1.5 text-[12px] font-semibold",
                        expiryState === "expired"
                          ? "text-red-800"
                          : expiryState === "soon"
                            ? "text-amber-900"
                            : "text-slate-800",
                      )}
                    >
                      {expiryState !== "valid" && expiryState !== "none" && (
                        <AlertCircle size={13} className="shrink-0" />
                      )}
                      {formatExpiry(source.expiryDate)}
                    </p>

                    {expiryState === "expired" && (
                      <p className="mt-1 text-[10px] font-medium text-red-800">
                        Expired
                      </p>
                    )}

                    {expiryState === "soon" && (
                      <p className="mt-1 text-[10px] font-medium text-amber-900">
                        Expires within 30 days
                      </p>
                    )}
                  </div>

                  <div className="col-span-2 rounded-lg border border-[#E3E8F2] p-2.5">
                    <span className="text-[11px] text-slate-500">Category</span>
                    <p className="mt-1.5 text-[12px] font-medium text-slate-800">
                      {source.category}
                    </p>
                  </div>
                </div>
              </section>

              <section aria-labelledby="usage-heading">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3
                    id="usage-heading"
                    className="text-[13px] font-semibold text-[#14213D]"
                  >
                    Used in {source.usedInCount ?? usedItems.length} content items
                  </h3>

                  <span
                    title="These are example links in the BrandGuard demo."
                    className="inline-flex items-center text-slate-400"
                  >
                    <AlertCircle size={13} />
                  </span>
                </div>

                <div className="overflow-hidden rounded-lg border border-[#E3E8F2]">
                  {usedItems.length > 0 ? (
                    usedItems.map((item, index) => (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => {
                          handleClose();
                          window.dispatchEvent(
                            new CustomEvent("brandguard:open-content", {
                              detail: { contentId: item.id },
                            }),
                          );
                        }}
                        className={cn(
                          "flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#2F5BEA]",
                          index > 0 && "border-t border-slate-100",
                        )}
                      >
                        <FileText
                          size={15}
                          className="shrink-0 text-slate-400"
                        />

                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[12px] font-medium text-slate-800">
                            {item.title}
                          </span>
                          <span className="mt-0.5 block text-[11px] text-slate-500">
                            {item.id} · {item.channel}
                          </span>
                        </span>

                        <ExternalLink
                          size={13}
                          className="shrink-0 text-slate-400"
                        />
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-4 text-[12px] text-slate-500">
                      No linked content items are available in this demo.
                    </div>
                  )}
                </div>
              </section>

              <section aria-labelledby="version-history-heading">
                <button
                  type="button"
                  aria-expanded={historyOpen}
                  onClick={() => setHistoryOpen((value) => !value)}
                  className="flex min-h-9 w-full items-center justify-between gap-2 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2F5BEA]"
                >
                  <span>
                    <span
                      id="version-history-heading"
                      className="block text-[13px] font-semibold text-[#14213D]"
                    >
                      Version history
                    </span>
                    <span className="mt-0.5 block text-[11px] text-slate-500">
                      {history.length} saved{" "}
                      {history.length === 1 ? "version" : "versions"}
                    </span>
                  </span>

                  {historyOpen ? (
                    <ChevronDown size={17} className="text-slate-500" />
                  ) : (
                    <ChevronRight size={17} className="text-slate-500" />
                  )}
                </button>

                {historyOpen && (
                  <div className="mt-2 space-y-2">
                    {history.length > 0 ? (
                      history.map((entry, index) => (
                        <div
                          key={`${entry.version}-${entry.date}`}
                          className="flex gap-2.5"
                        >
                          <div className="flex w-5 shrink-0 flex-col items-center">
                            <span
                              className={cn(
                                "flex h-5 w-5 items-center justify-center rounded-full border",
                                index === 0
                                  ? "border-blue-200 bg-blue-50 text-[#2F5BEA]"
                                  : "border-slate-200 bg-white text-slate-400",
                              )}
                            >
                              {index === 0 ? (
                                <Check size={11} />
                              ) : (
                                <span className="text-[9px]">
                                  {entry.version}
                                </span>
                              )}
                            </span>

                            {index < history.length - 1 && (
                              <span className="mt-1 min-h-3 w-px flex-1 bg-slate-200" />
                            )}
                          </div>

                          <div className="min-w-0 flex-1 rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
                            <div className="flex flex-wrap items-center justify-between gap-1.5">
                              <span className="text-[12px] font-semibold text-slate-800">
                                Version {entry.version}
                                {index === 0 ? " · Current" : ""}
                              </span>
                              <span className="text-[10px] text-slate-500">
                                {entry.date}
                              </span>
                            </div>

                            <p className="mt-1 text-[12px] leading-4 text-slate-600">
                              {entry.note}
                            </p>

                            <p className="mt-1.5 text-[11px] text-slate-500">
                              Changed by {entry.owner}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="rounded-lg bg-slate-50 p-3 text-[12px] text-slate-500">
                        No previous versions are available.
                      </p>
                    )}
                  </div>
                )}
              </section>
            </div>

            <footer className="border-t border-[#E3E8F2] bg-white px-4 py-3">
              <div aria-live="polite" className="mb-2 min-h-4">
                {copied && (
                  <p className="flex items-center gap-1.5 text-[12px] font-medium text-emerald-800">
                    <Check size={13} />
                    Source ID copied
                  </p>
                )}

                {copyError && (
                  <p className="text-[12px] text-red-700">
                    Copy wasn't available. Select and copy the source ID above.
                  </p>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-lg border border-[#E3E8F2] bg-white px-3 text-[12px] font-semibold text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2F5BEA] focus-visible:ring-offset-2"
                >
                  {copied ? <Check size={15} /> : <Clipboard size={15} />}
                  {copied ? "Copied" : "Copy source ID"}
                </button>

                {isAdmin && (
                  <button
                    type="button"
                    onClick={() => onEdit?.(source)}
                    className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-lg bg-[#2F5BEA] px-3 text-[12px] font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2F5BEA] focus-visible:ring-offset-2"
                  >
                    <Pencil size={14} />
                    Edit this source
                  </button>
                )}
              </div>
            </footer>
          </>
        )}
      </aside>
    </div>
  );
}

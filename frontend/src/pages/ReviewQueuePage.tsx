import { useEffect, useMemo, useState } from "react";
import { Check, CheckCircle2, CircleAlert, Clock3, Send, Undo2 } from "lucide-react";
import { api } from "@/api/client";
import { getContent, listRevisions, type ContentRecord, type ContentStatus, type Revision } from "@/api/content";
import { listFindings, type Finding } from "@/api/checks";
import { listSources } from "@/api/sources";
import {
  addComment,
  approveContent,
  listComments,
  listReviewQueue,
  publishContent,
  requestChanges,
  type ContentComment,
  type ReviewQueueItem,
} from "@/api/review";
import { SourceChip } from "@/components/shared/SourceChip";
import SourceDrawer from "@/components/shared/SourceDrawer";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import type { BrandSource } from "@/types";
import { cn } from "@/lib/utils";

type Tab = "All" | "In Review" | "Changes requested" | "Approved";
const TABS: Tab[] = ["All", "In Review", "Changes requested", "Approved"];

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "";
}

function StatusPill({ status }: { status: ContentStatus }) {
  const style =
    status === "In Review" ? "border-amber-200 bg-amber-50 text-amber-800"
      : status === "Approved" || status === "Published" ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : "border-red-200 bg-red-50 text-red-700";
  const Icon = status === "In Review" ? Clock3 : status === "Changes requested" ? CircleAlert : CheckCircle2;
  return <span className={cn("inline-flex h-6 shrink-0 items-center gap-1 rounded-full border px-2 text-[11px] font-semibold", style)}><Icon size={11} />{status}</span>;
}

type Detail = {
  content: ContentRecord;
  findings: Finding[];
  comments: ContentComment[];
  revisions: Revision[];
};

export default function ReviewQueuePage() {
  const [role, setRole] = useState<string | null>(null);
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("All");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [sources, setSources] = useState<BrandSource[]>([]);
  const [drawerSource, setDrawerSource] = useState<BrandSource | null>(null);
  const [commentText, setCommentText] = useState("");
  const [sendBackOpen, setSendBackOpen] = useState(false);
  const [sendBackText, setSendBackText] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };

  const canReview = role === "reviewer" || role === "manager" || role === "admin";
  const canPublish = role === "manager" || role === "admin";

  const loadQueue = async (): Promise<ReviewQueueItem[]> => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      const list = await listReviewQueue();
      setItems(list);
      return list;
    } catch (error: unknown) {
      const msg = errorText(error);
      setQueueError(msg);
      throw error;
    } finally {
      setQueueLoading(false);
    }
  };

  const loadDetail = async (id: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const [content, findings, comments, revisions] = await Promise.all([
        getContent(id),
        listFindings(id),
        listComments(id),
        listRevisions(id),
      ]);
      setDetail({ content, findings, comments, revisions });
    } catch (error: unknown) {
      const msg = errorText(error);
      setDetailError(msg);
      notify(`Could not load content: ${msg}`);
      throw error;
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    api.getMe().then((me) => setRole(me.role)).catch(() => setRole(null));
    listSources().then(setSources).catch(() => setSources([]));
    loadQueue()
      .then((list) => setSelectedId((current) => current ?? list[0]?.id ?? null))
      .catch(() => {});
    // Loads once on mount; later refreshes call loadQueue directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    loadDetail(selectedId).catch(() => {});
  }, [selectedId]);

  const visibleItems = useMemo(
    () => items.filter((item) =>
      (tab === "All" || item.status === tab) &&
      `${item.title} ${item.channel} ${item.ownerName}`.toLowerCase().includes(search.toLowerCase()),
    ),
    [items, tab, search],
  );

  const selectedItem = items.find((item) => item.id === selectedId) ?? null;
  const openFindings = detail?.findings.filter((f) => f.status === "open") ?? [];

  /** Runs a workflow action, then refreshes the queue and the open item. */
  const runAction = async (action: () => Promise<unknown>, success: string): Promise<boolean> => {
    setBusy(true);
    try {
      await action();
      const list = await loadQueue();
      const stillThere = list.some((item) => item.id === selectedId);
      if (selectedId && stillThere) await loadDetail(selectedId);
      else setSelectedId(list[0]?.id ?? null);
      notify(success);
      return true;
    } catch (error: unknown) {
      notify(errorText(error));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const approve = () => selectedId && runAction(() => approveContent(selectedId), "Approved for publication");
  const publish = () => selectedId && runAction(() => publishContent(selectedId), "Published");

  const sendBack = async () => {
    const value = sendBackText.trim();
    if (!selectedId || !value) return;
    const ok = await runAction(() => requestChanges(selectedId, value), "Sent back to the creator");
    if (ok) {
      setSendBackOpen(false);
      setSendBackText("");
    }
  };

  const postComment = async () => {
    const value = commentText.trim();
    if (!selectedId || !value || busy) return;
    setBusy(true);
    try {
      await addComment(selectedId, value);
      setCommentText("");
      await loadDetail(selectedId);
      notify("Comment added");
    } catch (error: unknown) {
      notify(errorText(error));
    } finally {
      setBusy(false);
    }
  };

  if (role === "creator") {
    return (
      <div className="p-6 text-sm text-slate-600">
        The review queue is for reviewers and managers. Creators can follow their drafts on the Content page.
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden text-slate-800">
      <div className="flex flex-col lg:grid lg:grid-cols-[minmax(0,40fr)_minmax(0,60fr)] min-h-0 flex-1 gap-3 overflow-y-auto lg:overflow-hidden">
        <section className="flex min-h-[360px] lg:min-h-0 flex-col overflow-hidden rounded-xl border border-[#DDE7F5] bg-white">
          <header className="flex flex-wrap items-center justify-between gap-3 px-4 pb-3 pt-4">
            <div>
              <h1 className="text-[18px] font-semibold text-[#14213D]">Content for Review</h1>
              <p className="mt-1 text-[12px] text-slate-500">Approve, send back, or publish content.</p>
            </div>
            <input
              aria-label="Search content"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search content..."
              className="min-h-[40px] sm:min-h-0 h-10 sm:h-9 w-full sm:w-[160px] rounded-lg border border-slate-200 px-3 text-[12px] outline-none focus:border-blue-300"
            />
          </header>
          <div className="flex gap-4 overflow-x-auto border-b border-slate-100 px-4" role="tablist">
            {TABS.map((item) => {
              const count = item === "All" ? items.length : items.filter((i) => i.status === item).length;
              return (
                <button
                  key={item}
                  role="tab"
                  aria-selected={tab === item}
                  type="button"
                  onClick={() => setTab(item)}
                  className={cn(
                    "whitespace-nowrap py-2.5 min-h-[40px] flex items-center text-[12px]",
                    tab === item ? "border-b-2 border-blue-600 font-semibold text-blue-600" : "text-slate-500 hover:text-slate-800"
                  )}
                >
                  {item} ({count})
                </button>
              );
            })}
          </div>
          <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto p-3">
            {queueError ? (
              <ErrorState
                title="Couldn't load review queue"
                description={queueError}
                onRetry={() => {
                  loadQueue()
                    .then((list) => setSelectedId((c) => c ?? list[0]?.id ?? null))
                    .catch(() => {});
                }}
                className="m-2"
              />
            ) : queueLoading ? (
              <LoadingState label="Loading review queue" rows={4} className="m-2" />
            ) : visibleItems.length === 0 ? (
              <EmptyState
                title={items.length === 0 ? "No content waiting for review" : "No matching content"}
                description={
                  items.length === 0
                    ? "All submitted content has been reviewed or published."
                    : "Try changing your search term or active tab filter."
                }
                className="m-2"
              />
            ) : (
              visibleItems.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={cn(
                    "flex w-full min-h-[44px] items-center gap-3 rounded-[10px] border px-3 py-2.5 text-left transition",
                    selectedId === item.id ? "border-[#8DB8FF] bg-[#EDF5FF]" : "border-slate-100 hover:bg-slate-50"
                  )}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12px] font-semibold text-[#14213D]">{item.title}</span>
                    <span className="mt-1 block truncate text-[10px] text-slate-500">
                      {item.channel} · {item.ownerName} · {formatDate(item.submittedAt ?? item.updatedAt)}
                    </span>
                  </span>
                  <StatusPill status={item.status} />
                </button>
              ))
            )}
          </div>
        </section>

        <section className="flex min-h-[480px] lg:min-h-0 flex-col overflow-hidden rounded-xl border border-[#DDE7F5] bg-white">
          {!selectedId ? (
            <EmptyState
              title="No item selected"
              description="Select an item from the review queue on the left to review its content, findings, and revisions."
              className="m-6"
            />
          ) : detailError ? (
            <ErrorState
              title="Couldn't load content details"
              description={detailError}
              onRetry={() => {
                if (selectedId) void loadDetail(selectedId);
              }}
              className="m-6"
            />
          ) : detailLoading ? (
            <LoadingState label="Loading content details" rows={6} className="m-6" />
          ) : !detail || !selectedItem ? (
            <EmptyState
              title="Content not found"
              description="The selected content could not be displayed."
              className="m-6"
            />
          ) : (
            <>
              <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
                <div className="min-w-0">
                  <h2 className="truncate text-[16px] font-semibold text-[#14213D]">{selectedItem.title}</h2>
                  <p className="mt-1 text-[12px] text-slate-500">
                    {selectedItem.channel} · Owner {selectedItem.ownerName} · Updated {formatDate(selectedItem.updatedAt)}
                  </p>
                </div>
                <StatusPill status={detail.content.status} />
              </header>

              <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
                <section>
                  <h3 className="mb-2 text-[13px] font-semibold text-[#14213D]">Draft</h3>
                  <p className="whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50 p-3 text-[12px] leading-relaxed text-slate-700">
                    {detail.content.bodyText || "No text"}
                  </p>
                </section>

                <section>
                  <h3 className="mb-2 text-[13px] font-semibold text-[#14213D]">Open findings ({openFindings.length})</h3>
                  {openFindings.length === 0 ? (
                    <p className="text-xs text-emerald-700">No open findings.</p>
                  ) : (
                    <div className="space-y-2">
                      {openFindings.map((finding) => (
                        <article key={finding.id} className="rounded-lg border border-slate-200 p-2.5">
                          <div className="flex items-center gap-2">
                            <SeverityBadge severity={finding.severity} />
                            <h4 className="min-w-0 flex-1 truncate text-[12px] font-semibold text-[#14213D]">{finding.title}</h4>
                            <span className="text-[10px] text-slate-500">{Math.round(finding.confidence * 100)}%</span>
                          </div>
                          <p className="mt-1.5 text-[11px] leading-relaxed text-slate-600">{finding.reason}</p>
                          <div className="mt-2">
                            <SourceChip
                              sourceId={finding.sourceId}
                              version={finding.sourceVersion}
                              category={sources.find((s) => s.id === finding.sourceId)?.category ?? "Guideline"}
                              onClick={() => setDrawerSource(sources.find((s) => s.id === finding.sourceId) ?? null)}
                            />
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <h3 className="mb-2 text-[13px] font-semibold text-[#14213D]">Comments</h3>
                  <div className="space-y-1.5">
                    {detail.comments.map((c) => (
                      <p key={c.id} className="text-[11px] text-slate-600">
                        <span className="font-semibold text-slate-700">{c.authorName}</span>{" "}
                        <span className="text-slate-400">{formatDate(c.createdAt)}</span>
                        <br />
                        {c.body}
                      </p>
                    ))}
                    {detail.comments.length === 0 && <p className="text-xs text-slate-400">No comments yet.</p>}
                  </div>
                  {canReview && (
                    <div className="mt-2 flex flex-col sm:flex-row gap-2">
                      <input
                        aria-label="Add a comment"
                        value={commentText}
                        disabled={busy}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Add a comment..."
                        className="min-h-[40px] flex-1 rounded-lg border border-slate-200 px-3 text-[12px] outline-none focus:border-blue-300"
                      />
                      <button
                        type="button"
                        onClick={() => void postComment()}
                        disabled={!commentText.trim() || busy}
                        className="inline-flex min-h-[40px] items-center justify-center gap-1 rounded-lg bg-blue-600 px-4 text-[11px] font-semibold text-white disabled:bg-blue-200"
                      >
                        <Send size={12} />Post
                      </button>
                    </div>
                  )}
                </section>

                <section>
                  <h3 className="mb-2 text-[13px] font-semibold text-[#14213D]">Revision history</h3>
                  <ol className="space-y-2">
                    {detail.revisions.map((r, i) => (
                      <li key={`${r.createdAt}-${i}`} className="text-[11px] text-slate-600">
                        <span className="font-semibold text-slate-700">{r.actorLabel || "System"}</span> {r.action}
                        {r.toStatus ? <> → <span className="font-medium">{r.toStatus}</span></> : null}
                        <span className="ml-2 text-slate-400">{formatDate(r.createdAt)}</span>
                        {r.detail && r.detail !== r.action ? <div className="text-slate-500">{r.detail}</div> : null}
                      </li>
                    ))}
                    {detail.revisions.length === 0 && <p className="text-xs text-slate-400">No revision history recorded.</p>}
                  </ol>
                </section>
              </div>

              <footer className="flex flex-wrap gap-2.5 border-t border-slate-100 px-4 py-3">
                {canReview && detail.content.status === "In Review" && (
                  <>
                    <button
                      type="button"
                      onClick={() => void approve()}
                      disabled={busy || detailLoading}
                      className="inline-flex min-h-[40px] flex-1 items-center justify-center gap-2 rounded-lg bg-[#2F73F6] text-[12px] font-semibold text-white disabled:bg-blue-200"
                    >
                      <Check size={16} />Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => setSendBackOpen(true)}
                      disabled={busy || detailLoading}
                      className="inline-flex min-h-[40px] flex-1 items-center justify-center gap-2 rounded-lg border border-blue-400 bg-white text-[12px] font-semibold text-blue-600 disabled:opacity-50"
                    >
                      <Undo2 size={15} />Send back
                    </button>
                  </>
                )}
                {canPublish && detail.content.status === "Approved" && (
                  <button
                    type="button"
                    onClick={() => void publish()}
                    disabled={busy || detailLoading}
                    className="inline-flex min-h-[40px] flex-1 items-center justify-center gap-2 rounded-lg border border-blue-300 bg-white text-[12px] font-semibold text-blue-600 disabled:opacity-50"
                  >
                    <Send size={15} />Publish
                  </button>
                )}
                {!((canReview && detail.content.status === "In Review") || (canPublish && detail.content.status === "Approved")) && (
                  <p className="text-xs text-slate-500">No action is needed from you for this status.</p>
                )}
              </footer>
            </>
          )}
        </section>
      </div>

      {sendBackOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/35 p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="send-back-title" className="w-full max-w-[420px] rounded-xl border border-slate-200 bg-white p-5 shadow-2xl">
            <h2 id="send-back-title" className="text-[16px] font-semibold text-[#14213D]">Send content back</h2>
            <p className="mt-1 text-[12px] text-slate-500">Tell the creator what needs to change. A comment is required.</p>
            <textarea
              autoFocus
              value={sendBackText}
              onChange={(e) => setSendBackText(e.target.value)}
              placeholder="Explain the changes needed..."
              className="mt-3 min-h-[110px] w-full rounded-lg border border-slate-200 p-3 text-[12px] outline-none focus:border-blue-400"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSendBackOpen(false)}
                disabled={busy}
                className="min-h-[40px] rounded-lg border border-slate-200 px-4 text-[12px] text-slate-600"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void sendBack()}
                disabled={!sendBackText.trim() || busy}
                className="min-h-[40px] rounded-lg bg-blue-600 px-4 text-[12px] font-semibold text-white disabled:bg-blue-200"
              >
                Send back
              </button>
            </div>
          </div>
        </div>
      )}

      <SourceDrawer source={drawerSource} onClose={() => setDrawerSource(null)} />
      {toast && <div role="status" className="fixed bottom-4 right-4 z-[80] rounded-lg bg-slate-900 px-4 py-2 text-xs text-white shadow-lg">{toast}</div>}
    </div>
  );
}

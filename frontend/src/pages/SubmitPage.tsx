import { useEffect, useRef, useState, type FormEvent } from "react";

import { PageHeader } from "@/components/shared/PageHeader";
import {
  AttachmentList,
  FileDropZone,
  HoldNotice,
  VisualFindingsView,
} from "@/components/submissions";
import {
  attachmentFileUrl,
  createSubmission,
  deleteAttachment,
  getSubmission,
  getSubmissionFindings,
  listAttachments,
  pollAttachments,
  submitForChecking,
  uploadAttachment,
  type Attachment,
  type Submission,
  type SubmissionChannel,
  type SubmissionFinding,
  type SubmissionKind,
} from "@/api/submissions";
import type { UserRole } from "@/types";

const KIND_OPTIONS: { value: SubmissionKind; label: string }[] = [
  { value: "script", label: "Script" },
  { value: "marketing_idea", label: "Marketing idea" },
  { value: "design", label: "Product design" },
  { value: "image", label: "Image" },
];
const CHANNEL_OPTIONS: SubmissionChannel[] = ["General", "Website", "Instagram", "Email", "Ad"];
const TEAM_OPTIONS = ["Marketing", "Sales", "Brand", "Legal", "Product", "Design", "HR", "Support"];

const BUSY = (a: Attachment) => a.readStatus === "pending" || a.readStatus === "reading";

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}

export default function SubmitPage({ role }: { role: UserRole }) {
  if (role === "reviewer") {
    return (
      <div className="space-y-4 overflow-y-auto">
        <PageHeader title="Submit for checking" description="Reviewers do not submit content. Use the review queue." />
      </div>
    );
  }
  return <SubmitWorkspace />;
}

function SubmitWorkspace() {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [findings, setFindings] = useState<SubmissionFinding[]>([]);
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({});
  const [checking, setChecking] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const imageUrlsRef = useRef<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Form state for a new submission.
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<SubmissionKind>("script");
  const [team, setTeam] = useState("Marketing");
  const [channel, setChannel] = useState<SubmissionChannel>("General");
  const [bodyText, setBodyText] = useState("");

  // Keep the attachment list fresh while any file is pending or being read.
  useEffect(() => {
    if (!submission || !checking) return;
    return pollAttachments(submission.id, (list) => {
      setAttachments(list);
      if (!list.some(BUSY)) setChecking(false);
    });
  }, [submission, checking]);

  // Load the latest submission state and findings when checking ends, after a text-only wait,
  // and once a submission is created.
  useEffect(() => {
    if (!submission || checking) return;
    let cancelled = false;
    async function refresh() {
      if (!submission) return;
      try {
        const [fresh, list, found] = await Promise.all([
          getSubmission(submission.id),
          listAttachments(submission.id),
          getSubmissionFindings(submission.id),
        ]);
        if (cancelled) return;
        setSubmission(fresh);
        setAttachments(list);
        setFindings(found);
      } catch (err) {
        if (!cancelled) setError(errorText(err));
      }
    }
    void refresh();
    return () => {
      cancelled = true;
    };
  }, [checking, refreshKey, submission?.id]);

  // Load the image for each image attachment that has visual findings. Each image loads once.
  useEffect(() => {
    if (!submission) return;
    let cancelled = false;
    attachments
      .filter((a) => a.kind === "image")
      .forEach((a) => {
        if (imageUrlsRef.current[a.id]) return;
        attachmentFileUrl(submission.id, a.id)
          .then((url) => {
            if (cancelled) URL.revokeObjectURL(url);
            else {
              imageUrlsRef.current[a.id] = url;
              setImageUrls({ ...imageUrlsRef.current });
            }
          })
          .catch(() => undefined);
      });
    return () => {
      cancelled = true;
    };
  }, [submission, attachments, findings]);

  // Release object URLs only when the page closes.
  useEffect(() => {
    return () => {
      Object.values(imageUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createSubmission({ title: title.trim(), kind, team, channel, bodyText });
      setSubmission(created);
      setAttachments([]);
      setFindings([]);
      setNotice(null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleFiles(files: File[]) {
    if (!submission) return;
    setBusy(true);
    setError(null);
    const failures: string[] = [];
    for (const file of files) {
      try {
        await uploadAttachment(submission.id, file);
      } catch (err) {
        failures.push(`${file.name}: ${errorText(err)}`);
      }
    }
    try {
      setAttachments(await listAttachments(submission.id));
    } catch (err) {
      failures.push(errorText(err));
    }
    if (failures.length) setError(failures.join(" "));
    setBusy(false);
  }

  async function handleDelete(attachmentId: string) {
    if (!submission) return;
    setError(null);
    try {
      await deleteAttachment(submission.id, attachmentId);
      setAttachments(await listAttachments(submission.id));
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function handleSubmit() {
    if (!submission) return;
    setError(null);
    setNotice(null);
    try {
      const started = await submitForChecking(submission.id);
      if (started.queued > 0) {
        setNotice(`Checking ${started.queued} file${started.queued === 1 ? "" : "s"}. Results appear below.`);
        setChecking(true);
      } else {
        setNotice("Checking the text. Results appear below.");
        window.setTimeout(() => setRefreshKey((k) => k + 1), 4000);
      }
    } catch (err) {
      setError(errorText(err));
    }
  }

  if (!submission) {
    return (
      <div className="mx-auto h-full w-full max-w-2xl space-y-4 overflow-y-auto pb-6">
        <PageHeader title="Submit for checking" description="Send a script, marketing idea, product design or image for a brand check. A manager sees anything that is held." />
        <form onSubmit={handleCreate} className="max-w-2xl space-y-4 rounded-xl border border-slate-200 bg-white p-5">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Title</span>
            <input
              required
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block text-sm">
              <span className="font-medium text-slate-700">Kind</span>
              <select value={kind} onChange={(e) => setKind(e.target.value as SubmissionKind)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
                {KIND_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-medium text-slate-700">Team</span>
              <select value={team} onChange={(e) => setTeam(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
                {TEAM_OPTIONS.map((t) => <option key={t}>{t}</option>)}
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-medium text-slate-700">Channel</span>
              <select value={channel} onChange={(e) => setChannel(e.target.value as SubmissionChannel)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
                {CHANNEL_OPTIONS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
          </div>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Text (optional)</span>
            <textarea
              rows={6}
              maxLength={50000}
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          <button type="submit" disabled={busy || !title.trim()} className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            Create submission
          </button>
        </form>
      </div>
    );
  }

  const held = submission.hold !== null;
  const canChange = !held && !checking && !busy;
  const visualAttachments = attachments.filter((a) => a.kind === "image");
  // An image finding is drawn on its picture only when that picture has loaded. Otherwise it is
  // listed below, so no finding is hidden when a preview fails to load.
  // Must match the types VisualFindingsView draws on the picture (image and accessibility).
  const DRAWN_TYPES = ["image", "accessibility"];
  const isDrawn = (f: SubmissionFinding) =>
    DRAWN_TYPES.includes(f.type) && (f.attachmentIds ?? []).some((id) => Boolean(imageUrls[id]));
  // The same finding can arrive twice (once linked to the picture, once not). Show each one once,
  // and never repeat in the list a finding that is already drawn on its picture.
  const keyOf = (f: SubmissionFinding) => `${f.type}|${f.title}|${f.reason}`;
  const drawnKeys = new Set(findings.filter(isDrawn).map(keyOf));
  const seenKeys = new Set<string>();
  const otherFindings = findings.filter((f) => {
    const key = keyOf(f);
    if (isDrawn(f) || drawnKeys.has(key) || seenKeys.has(key)) return false;
    seenKeys.add(key);
    return true;
  });

  return (
    <div className="mx-auto h-full w-full max-w-2xl space-y-4 overflow-y-auto pb-6">
      <PageHeader
        title={submission.title}
        description={`${KIND_OPTIONS.find((o) => o.value === submission.kind)?.label ?? submission.kind} · ${submission.channel} · ${submission.team}`}
      />
      <HoldNotice hold={submission.hold} />

      <section className="max-w-3xl space-y-3 rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-800">Files</h2>
        <FileDropZone
          existingCount={attachments.length}
          disabled={!canChange}
          onFiles={(files) => void handleFiles(files)}
        />
        <AttachmentList attachments={attachments} canDelete={canChange} onDelete={(id) => void handleDelete(id)} />
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        {notice && <p role="status" className="text-sm text-slate-600">{notice}</p>}
        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={!canChange || checking}
          className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {checking ? "Checking…" : "Submit for checking"}
        </button>
      </section>

      {!held && findings.length === 0 && !checking && (
        <p className="text-sm text-slate-500">No findings yet. Submit the content for checking to see results.</p>
      )}

      {visualAttachments.map((a) =>
        imageUrls[a.id] ? (
          <VisualFindingsView
            key={a.id}
            imageUrl={imageUrls[a.id]}
            alt={a.filename}
            findings={findings.filter((f) => f.attachmentIds?.includes(a.id))}
            className="max-w-sm"
          />
        ) : (
          <p key={a.id} className="text-xs text-slate-500">
            Preview of {a.filename} is not available. Its findings are listed below.
          </p>
        ),
      )}

      {otherFindings.length > 0 && (
        <section className="max-w-3xl space-y-3">
          <h2 className="text-sm font-semibold text-slate-800">Findings</h2>
          {otherFindings.map((f) => (
            <article key={f.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{f.severity}</p>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-1 text-sm text-slate-700">{f.reason}</p>
              {f.suggestedFix && <p className="mt-2 text-sm text-slate-600"><span className="font-medium">Suggested fix: </span>{f.suggestedFix}</p>}
              {f.needsHumanReview && <p className="mt-2 text-xs text-slate-500">A person should check this before anything changes.</p>}
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

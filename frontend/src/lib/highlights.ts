import type { Finding } from "@/api/checks";

export interface TextSegment {
  text: string;
  findingId: string | null;
  severity: Finding["severity"] | null;
}

export const HIGHLIGHT_CLASS: Record<Finding["severity"], string> = {
  critical: "bg-red-100 underline decoration-red-500 cursor-pointer",
  warning: "bg-amber-100 underline decoration-amber-500 cursor-pointer",
  info: "bg-blue-100 underline decoration-blue-500 cursor-pointer",
};

/**
 * Split plain body text into segments so each open finding's span can be rendered
 * with its severity colour. Overlapping spans are skipped (their card still shows).
 *
 * Note: backend offsets count Unicode code points; JavaScript string indices count
 * UTF-16 units. They match for plain ASCII and BMP text. Emoji will shift highlights.
 */
export function buildSegments(
  text: string,
  findings: Pick<Finding, "id" | "start" | "end" | "severity" | "status">[],
): TextSegment[] {
  const open = findings
    .filter((f) => f.status === "open" && f.start !== null && f.end !== null && f.end > f.start)
    .sort((a, b) => (a.start as number) - (b.start as number));

  const segments: TextSegment[] = [];
  let cursor = 0;
  for (const f of open) {
    const start = Math.max(0, Math.min(f.start as number, text.length));
    const end = Math.max(start, Math.min(f.end as number, text.length));
    if (start < cursor) continue;
    if (start > cursor) {
      segments.push({ text: text.slice(cursor, start), findingId: null, severity: null });
    }
    segments.push({ text: text.slice(start, end), findingId: f.id, severity: f.severity });
    cursor = end;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), findingId: null, severity: null });
  }
  return segments;
}

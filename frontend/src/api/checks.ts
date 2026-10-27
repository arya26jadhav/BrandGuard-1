import { apiRequest } from "./client";

export type FindingSeverity = "critical" | "warning" | "info";
export type FindingStatus = "open" | "accepted" | "edited" | "rejected" | "resolved";

export interface Finding {
  id: string;
  contentId: string;
  type: string;
  start: number | null;
  end: number | null;
  bbox: number[] | null;
  severity: FindingSeverity;
  title: string;
  reason: string;
  sourceId: string;
  sourceVersion: number;
  originalText: string | null;
  suggestedFix: string;
  confidence: number;
  aiGenerated: boolean;
  needsHumanReview: boolean;
  status: FindingStatus;
  suggestionKind: string;
  checkRunId: string;
}

export interface CheckResult {
  checkRunId: string;
  model: string;
  /** success | cached | fallback. "fallback" means the AI stage did not run and only rules results are shown. */
  aiStatus: "success" | "cached" | "fallback";
  /** Server-side detail for logs. Do not show this text to users. */
  aiError: string | null;
  rulesOnlyFallback: boolean;
  findings: Finding[];
}

export function runCheck(contentId: string): Promise<CheckResult> {
  return apiRequest<CheckResult>(`/api/content/${contentId}/check`, { method: "POST" });
}

export function listFindings(contentId: string): Promise<Finding[]> {
  return apiRequest<Finding[]>(`/api/content/${contentId}/findings`);
}

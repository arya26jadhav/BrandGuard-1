import { apiRequest } from "./client";
import type { ContentStatus } from "./content";

export interface ReviewSummary {
  pendingReview: number;
  changesRequested: number;
}

export interface ReviewQueueItem {
  id: string;
  title: string;
  channel: string;
  status: ContentStatus;
  ownerName: string;
  updatedAt: string;
  submittedAt: string | null;
  openFindings: number;
}

export interface ContentComment {
  id: string;
  body: string;
  authorId: string;
  authorName: string;
  commentType: "review" | "decision" | "general" | "system";
  findingId: string | null;
  createdAt: string;
}

export interface WorkflowResult {
  id: string;
  status: ContentStatus;
}

const path = (id: string) => `/api/content/${encodeURIComponent(id)}`;

export const getReviewSummary = (): Promise<ReviewSummary> =>
  apiRequest<ReviewSummary>("/api/review/summary");

export const listReviewQueue = (): Promise<ReviewQueueItem[]> =>
  apiRequest<ReviewQueueItem[]>("/api/review/queue");

export const submitForReview = (id: string): Promise<WorkflowResult> =>
  apiRequest<WorkflowResult>(`${path(id)}/submit`, { method: "POST" });

export const approveContent = (id: string): Promise<WorkflowResult> =>
  apiRequest<WorkflowResult>(`${path(id)}/approve`, { method: "POST" });

export const requestChanges = (id: string, comment: string): Promise<WorkflowResult> =>
  apiRequest<WorkflowResult>(`${path(id)}/request-changes`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });

export const publishContent = (id: string): Promise<WorkflowResult> =>
  apiRequest<WorkflowResult>(`${path(id)}/publish`, { method: "POST" });

export const listComments = (id: string): Promise<ContentComment[]> =>
  apiRequest<ContentComment[]>(`${path(id)}/comments`);

export const addComment = (id: string, body: string, findingId?: string): Promise<{ ok: boolean }> =>
  apiRequest<{ ok: boolean }>(`${path(id)}/comments`, {
    method: "POST",
    body: JSON.stringify({ body, findingId: findingId ?? null }),
  });

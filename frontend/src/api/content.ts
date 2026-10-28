import { apiRequest } from "./client";

export type ContentChannel = "Website" | "Instagram" | "Email" | "Ad";
export type ContentTeam = "Marketing" | "Sales" | "Brand" | "Legal" | "Product" | "Design" | "HR" | "Support";
export type ContentStatus = "Draft" | "Checked" | "Fixing" | "In Review" | "Changes requested" | "Approved" | "Published" | "Needs revalidation";

export interface ContentRecord {
  id: string;
  title: string;
  channel: ContentChannel;
  team: ContentTeam;
  status: ContentStatus;
  bodyText: string;
  bodyHtml: string;
  ownerId: string;
  createdAt: string;
  updatedAt: string;
  currentVersion: number;
  thumbnailArt: string | null;
  imageUrl: string | null;
  altText: string | null;
}

export interface ContentInput {
  title: string;
  channel: ContentChannel;
  team: ContentTeam;
  bodyText: string;
  bodyHtml: string;
  thumbnailArt?: string | null;
  imageUrl?: string | null;
  altText?: string | null;
}

export type ContentPatch = Partial<Pick<ContentInput, "title" | "channel" | "bodyText" | "bodyHtml" | "altText">>;

export interface ContentVersion {
  version: number;
  changeType: "initial" | "ai_fix" | "human_edit" | "reviewer_edit" | "restore" | "other";
  actorLabel: string;
  note: string;
  createdAt: string;
  bodyText: string;
}

export interface Revision {
  actorLabel: string;
  kind: "person" | "ai";
  action: string;
  detail: string;
  fromStatus: ContentStatus | null;
  toStatus: ContentStatus | null;
  version: number | null;
  createdAt: string;
}

export const listContent = (): Promise<ContentRecord[]> =>
  apiRequest<ContentRecord[]>("/api/content");

export const createContent = (input: ContentInput): Promise<ContentRecord> =>
  apiRequest<ContentRecord>("/api/content", {
    method: "POST",
    body: JSON.stringify(input),
  });

export const getContent = (id: string): Promise<ContentRecord> =>
  apiRequest<ContentRecord>(`/api/content/${encodeURIComponent(id)}`);

export const updateContent = (id: string, patch: ContentPatch): Promise<ContentRecord> =>
  apiRequest<ContentRecord>(`/api/content/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });

export const listVersions = (id: string): Promise<ContentVersion[]> =>
  apiRequest<ContentVersion[]>(`/api/content/${encodeURIComponent(id)}/versions`);

export const listRevisions = (id: string): Promise<Revision[]> =>
  apiRequest<Revision[]>(`/api/content/${encodeURIComponent(id)}/revisions`);

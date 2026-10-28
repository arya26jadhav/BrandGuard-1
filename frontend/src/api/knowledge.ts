import { apiRequest } from "./client";

export interface ProductItem {
  id: string;
  name: string;
  line: string;
  status: "Active" | "Inactive";
}

export interface FactItem {
  id: string;
  productId: string | null;
  title: string;
  statement: string;
  factType: string;
  structuredValue: Record<string, unknown>;
  severityOnChange: "High" | "Medium";
  ownerId: string;
  version: number;
  validFrom: string;
  validUntil: string | null;
  status: "Active" | "Expiring soon" | "Expired";
  category: string;
  createdAt: string;
  updatedAt: string;
}

export interface FactHistoryItem {
  factId: string;
  version: number;
  statement: string;
  structuredValue: Record<string, unknown>;
  note: string;
  owner: string;
  changedBy: string | null;
  changedAt: string;
  validFrom: string;
  validUntil: string | null;
}

export interface GuidelineItem {
  id: string;
  shortName: string;
  title: string;
  text: string;
  category:
    | "Terminology"
    | "Claims & Legal"
    | "Tone of Voice"
    | "Formatting"
    | "Accessibility"
    | "Brand Assets"
    | "Security";
  ruleType: string;
  severity: "critical" | "warning" | "info";
  appliesToChannels: string[];
  requiredText: string | null;
  version: number;
  ownerId: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface GuidelineVersionItem {
  guidelineId: string;
  version: number;
  text: string;
  changedBy: string | null;
  changedByName: string | null;
  changeNote: string;
  changedAt: string;
}

export interface GlossaryItem {
  id: string;
  approvedTerm: string;
  avoidTerms: string[];
  kind: "term" | "product_name";
  explanation: string;
  isActive: boolean;
  createdAt: string;
}

export interface UploadGuidelinesResponse {
  count?: number;
  imported?: number;
  message?: string;
  [key: string]: unknown;
}

export async function getProducts(): Promise<ProductItem[]> {
  return apiRequest<ProductItem[]>("/api/knowledge/products");
}

export async function getFacts(): Promise<FactItem[]> {
  return apiRequest<FactItem[]>("/api/knowledge/facts");
}

export async function getFactHistory(factId: string): Promise<FactHistoryItem[]> {
  return apiRequest<FactHistoryItem[]>(`/api/knowledge/facts/${factId}/history`);
}

export async function getGuidelines(): Promise<GuidelineItem[]> {
  return apiRequest<GuidelineItem[]>("/api/knowledge/guidelines");
}

export async function getGuidelineVersions(guidelineId: string): Promise<GuidelineVersionItem[]> {
  return apiRequest<GuidelineVersionItem[]>(`/api/knowledge/guidelines/${guidelineId}/versions`);
}

export async function getGlossary(): Promise<GlossaryItem[]> {
  return apiRequest<GlossaryItem[]>("/api/knowledge/glossary");
}

export async function uploadGuidelinesFile(file: File): Promise<UploadGuidelinesResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<UploadGuidelinesResponse>("/api/knowledge/guidelines/upload", {
    method: "POST",
    body: formData,
  });
}


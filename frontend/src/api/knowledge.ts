import { apiRequest } from "./client";

export type FactStatus = "Active" | "Expiring soon" | "Expired";
export type FactSeverity = "High" | "Medium";

export interface FactRecord {
  id: string;
  productId: string | null;
  title: string;
  statement: string;
  factType: string;
  structuredValue: Record<string, unknown>;
  matchKeywords: string[];
  severityOnChange: FactSeverity;
  ownerId: string | null;
  version: number;
  validFrom: string;
  validUntil: string | null;
  status: FactStatus;
  category: string;
  updatedAt: string;
}

export interface FactHistoryItem {
  version: number;
  statement: string;
  note: string | null;
  owner: string;
  changedBy: string;
  changedAt: string;
  validFrom: string;
  validUntil: string | null;
}

export interface FactInput {
  title: string;
  statement: string;
  factType: string;
  productId?: string | null;
  structuredValue?: Record<string, unknown>;
  matchKeywords?: string[];
  matchRegex?: string | null;
  severityOnChange?: FactSeverity;
  category?: string;
  validFrom?: string;
  validUntil?: string | null;
  ownerId?: string | null;
  status?: FactStatus;
}

export interface FactUpdateInput {
  title?: string;
  statement?: string;
  status?: FactStatus;
  validUntil?: string | null;
  severityOnChange?: FactSeverity;
  note?: string;
}

export interface GuidelineRecord {
  id: string;
  shortName: string;
  title: string;
  text: string;
  category: string;
  ruleType: string;
  severity: "critical" | "warning" | "info";
  appliesToChannels: string[];
  requiredText: string | null;
  version: number;
  ownerId: string | null;
  isActive: boolean;
  updatedAt: string;
}

export interface GuidelineUpdateInput {
  text?: string;
  severity?: "critical" | "warning" | "info";
  isActive?: boolean;
}

export interface GuidelineCreateInput {
  shortName: string;
  title: string;
  text: string;
  category: string;
  ruleType?: string;
  severity?: "critical" | "warning" | "info";
  appliesToChannels?: string[];
  requiredText?: string | null;
}

export interface GlossaryRecord {
  id: string;
  approvedTerm: string;
  avoidTerms: string[];
  kind: "term" | "product_name";
  explanation: string;
  isActive: boolean;
}

export interface GlossaryCreateInput {
  approvedTerm: string;
  avoidTerms?: string[];
  kind: "term" | "product_name";
  explanation?: string;
}

export interface AssetRecord {
  id: string;
  label: string;
  assetType: string;
  version: number;
  status: string;
  hex: string | null;
  usageNote: string | null;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Facts endpoints
// ---------------------------------------------------------------------------

export const listFacts = (status?: FactStatus): Promise<FactRecord[]> => {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<FactRecord[]>(`/api/knowledge/facts${query}`);
};

export const getFact = (factId: string): Promise<FactRecord> =>
  apiRequest<FactRecord>(`/api/knowledge/facts/${encodeURIComponent(factId)}`);

export const createFact = (input: FactInput): Promise<FactRecord> => {
  const payload: Record<string, unknown> = {
    title: input.title,
    statement: input.statement,
    fact_type: input.factType,
    product_id: input.productId ?? null,
    structured_value: input.structuredValue ?? {},
    match_keywords: input.matchKeywords ?? [],
    match_regex: input.matchRegex ?? null,
    severity_on_change: input.severityOnChange ?? "Medium",
    category: input.category ?? "Brand",
  };
  if (input.validFrom) payload.valid_from = input.validFrom;
  if (input.validUntil !== undefined) payload.valid_until = input.validUntil;
  if (input.ownerId !== undefined) payload.owner_id = input.ownerId;
  if (input.status) payload.status = input.status;

  return apiRequest<FactRecord>("/api/knowledge/facts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

export const updateFact = (
  factId: string,
  input: FactUpdateInput,
): Promise<FactRecord> => {
  const payload: Record<string, unknown> = {};
  if (input.title !== undefined) payload.title = input.title;
  if (input.statement !== undefined) payload.statement = input.statement;
  if (input.status !== undefined) payload.status = input.status;
  if (input.validUntil !== undefined) payload.valid_until = input.validUntil;
  if (input.severityOnChange !== undefined) payload.severity_on_change = input.severityOnChange;
  if (input.note !== undefined) payload.note = input.note;

  return apiRequest<FactRecord>(`/api/knowledge/facts/${encodeURIComponent(factId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
};

export const getFactHistory = (factId: string): Promise<FactHistoryItem[]> =>
  apiRequest<FactHistoryItem[]>(
    `/api/knowledge/facts/${encodeURIComponent(factId)}/history`,
  );

// ---------------------------------------------------------------------------
// Guidelines endpoints
// ---------------------------------------------------------------------------

export const listGuidelines = (): Promise<GuidelineRecord[]> =>
  apiRequest<GuidelineRecord[]>("/api/knowledge/guidelines");

export const getGuideline = (guidelineId: string): Promise<GuidelineRecord> =>
  apiRequest<GuidelineRecord>(
    `/api/knowledge/guidelines/${encodeURIComponent(guidelineId)}`,
  );

export const updateGuideline = (
  guidelineId: string,
  input: GuidelineUpdateInput,
): Promise<GuidelineRecord> => {
  const payload: Record<string, unknown> = {};
  if (input.text !== undefined) payload.text = input.text;
  if (input.severity !== undefined) payload.severity = input.severity;
  if (input.isActive !== undefined) payload.is_active = input.isActive;

  return apiRequest<GuidelineRecord>(
    `/api/knowledge/guidelines/${encodeURIComponent(guidelineId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
};

export const createGuideline = (
  input: GuidelineCreateInput,
): Promise<GuidelineRecord> => {
  const payload: Record<string, unknown> = {
    short_name: input.shortName,
    title: input.title,
    text: input.text,
    category: input.category,
    rule_type: input.ruleType ?? "warning",
    severity: input.severity ?? "warning",
    applies_to_channels: input.appliesToChannels ?? [
      "Website",
      "Instagram",
      "Email",
      "Ad",
    ],
    required_text: input.requiredText ?? null,
  };

  return apiRequest<GuidelineRecord>("/api/knowledge/guidelines", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

// ---------------------------------------------------------------------------
// Glossary endpoints
// ---------------------------------------------------------------------------

export const listGlossary = (): Promise<GlossaryRecord[]> =>
  apiRequest<GlossaryRecord[]>("/api/knowledge/glossary");

export const createGlossaryTerm = (
  input: GlossaryCreateInput,
): Promise<GlossaryRecord> => {
  const payload = {
    approved_term: input.approvedTerm,
    avoid_terms: input.avoidTerms ?? [],
    kind: input.kind,
    explanation: input.explanation ?? "",
  };

  return apiRequest<GlossaryRecord>("/api/knowledge/glossary", {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

// ---------------------------------------------------------------------------
// Assets endpoints
// ---------------------------------------------------------------------------

export const listAssets = (assetType?: string): Promise<AssetRecord[]> => {
  const query = assetType ? `?asset_type=${encodeURIComponent(assetType)}` : "";
  return apiRequest<AssetRecord[]>(`/api/knowledge/assets${query}`);
};


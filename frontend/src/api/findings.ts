import { apiRequest } from "./client";
import type { Finding } from "./checks";

export type DecisionAction = "accept" | "edit" | "reject";

export interface DecisionInput {
  action: DecisionAction;
  editedText?: string;
  rejectReason?: string;
}

export interface DecisionResult {
  findingId: string;
  status: Finding["status"];
  /** Plain text of the draft after the decision (offsets in findings match this). */
  bodyText: string;
  /** Optional HTML of the draft, so bold and links survive an accept. */
  bodyHtml?: string | null;
  contentStatus: string;
  findings: Finding[];
}

/** Sends one accept, edit or reject for a single finding. */
export function decideFinding(findingId: string, input: DecisionInput): Promise<DecisionResult> {
  if (input.action === "edit" && !input.editedText?.trim()) {
    return Promise.reject(new Error("Enter the edited text before applying it."));
  }
  return apiRequest<DecisionResult>(`/api/findings/${findingId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

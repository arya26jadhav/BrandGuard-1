import { apiRequest } from "./client";

export interface AnalyticsKPIs {
  avgReviewMinutes: number | null;
  avgReviewItems: number;
  unresolvedIssues: number;
  outdatedPublishedPosts: number;
  suggestionsAcceptedPct: number | null;
  decisionCount: number;
}

export interface ViolatedRule {
  ruleId: string;
  label: string;
  count: number;
}

export interface RejectedSuggestion {
  type: string;
  label: string;
  count: number;
}

export interface IssueOverTime {
  date: string;
  critical: number;
  warning: number;
  info: number;
}

export interface TeamReviewTime {
  team: string;
  avgMinutes: number;
}

export interface AnalyticsSummaryResponse {
  kpis: AnalyticsKPIs;
  mostViolatedRules: ViolatedRule[];
  mostRejectedSuggestions: RejectedSuggestion[];
  issuesOverTime: IssueOverTime[];
  reviewTimeByTeam: TeamReviewTime[];
}

export async function getAnalyticsSummary(days: number = 30): Promise<AnalyticsSummaryResponse> {
  return apiRequest<AnalyticsSummaryResponse>(`/api/analytics/summary?days=${days}`);
}


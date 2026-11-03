import { apiRequest } from "./client";

export interface AlertItem {
  id: string;
  contentId: string | null;
  title: string;
  reason: string;
  priority: "High" | "Medium";
  status: "open" | "updated" | "dismissed";
  oldValue: string | null;
  newValue: string | null;
  createdAt: string;
  read: boolean;
}

export async function getAlerts(status?: "open" | "updated" | "dismissed"): Promise<AlertItem[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<AlertItem[]>(`/api/alerts${query}`);
}

export async function updateAlertStatus(
  id: string,
  patchOrStatus: ("updated" | "dismissed") | { status?: "updated" | "dismissed"; read?: boolean },
): Promise<AlertItem> {
  const body = typeof patchOrStatus === "string" ? { status: patchOrStatus } : patchOrStatus;
  return apiRequest<AlertItem>(`/api/alerts/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function markAllAlertsRead(): Promise<{ status: string }> {
  return apiRequest<{ status: string }>("/api/alerts/mark-all-read", {
    method: "POST",
  });
}

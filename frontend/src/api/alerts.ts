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
}

export async function getAlerts(status?: "open" | "updated" | "dismissed"): Promise<AlertItem[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<AlertItem[]>(`/api/alerts${query}`);
}

export async function updateAlertStatus(
  id: string,
  status: "updated" | "dismissed",
): Promise<AlertItem> {
  return apiRequest<AlertItem>(`/api/alerts/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}


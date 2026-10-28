import type { ContentItem } from "@/types";

export const mockContent: ContentItem[] = [
  { id: "content-001", title: "Tea Tree Face Wash — launch post", channel: "Instagram", owner: "Maya Chen", updatedAt: "Today, 10:42 AM", status: "Checked", findingCount: 3, severity: "critical" },
  { id: "content-002", title: "Sunscreen SPF 50 — summer creative", channel: "Paid ad", owner: "Sam Rivera", updatedAt: "Today, 9:18 AM", status: "In Review", findingCount: 2, severity: "warning" },
  { id: "content-003", title: "Daily skincare routine landing page", channel: "Website", owner: "Maya Chen", updatedAt: "Yesterday", status: "Approved", findingCount: 0 },
  { id: "content-004", title: "Welcome offer email", channel: "Email", owner: "Jordan Lee", updatedAt: "Yesterday", status: "Changes requested", findingCount: 1, severity: "warning" },
  { id: "content-005", title: "Tea Tree Face Wash product card", channel: "Website", owner: "Sam Rivera", updatedAt: "Oct 22, 2026", status: "Needs revalidation", findingCount: 1, severity: "critical" },
];

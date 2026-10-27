import type { BrandAlert } from "@/types";

export const mockAlerts: BrandAlert[] = [
  { id: "alert-001", factId: "FACT-027", title: "Sunscreen SPF 50 price changed", oldValue: "₹349", newValue: "₹399", affectedCount: 3, createdAt: "Today, 9:05 AM", status: "New" },
  { id: "alert-002", factId: "FACT-009", title: "Tea Tree Face Wash benefit wording updated", oldValue: "Controls acne", newValue: "Cleanses excess oil and impurities", affectedCount: 2, createdAt: "Oct 22, 2026", status: "In progress" },
];

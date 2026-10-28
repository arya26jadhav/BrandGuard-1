import type { BrandSource } from "@/types";

export const mockSources: BrandSource[] = [
  { id: "GUIDE-001", title: "GreenGlow voice and tone", category: "Guideline", version: 5, updatedAt: "Oct 20, 2026", owner: "Brand Team", status: "Active", excerpt: "Clear, calm, science-aware language. Avoid fear-based messaging and guaranteed outcomes." },
  { id: "GUIDE-022", title: "Skincare claims and disclaimers", category: "Disclaimer", version: 5, updatedAt: "Oct 18, 2026", owner: "Legal Team", status: "Active", excerpt: "Include ‘Results may vary from person to person.’ when applicable skincare results are discussed." },
  { id: "FACT-009", title: "Tea Tree Face Wash approved benefits", category: "Product fact", version: 2, updatedAt: "Oct 16, 2026", owner: "Product Team", status: "Active", excerpt: "Cleanses excess oil and impurities. Do not claim that it cures or removes acne." },
  { id: "FACT-014", title: "Approved skincare claims", category: "Product fact", version: 3, updatedAt: "Oct 16, 2026", owner: "Legal Team", status: "Active", excerpt: "No guaranteed, permanent, overnight, or 100% skin outcome claims are approved." },
  { id: "FACT-027", title: "Sunscreen SPF 50 retail price", category: "Product fact", version: 4, updatedAt: "Oct 25, 2026", owner: "Commerce Team", status: "Needs review", excerpt: "Previous price ₹349. New approved price ₹399. Revalidate content that still shows ₹349." },
  { id: "ASSET-001", title: "GreenGlow master logo pack", category: "Asset", version: 4, updatedAt: "Oct 12, 2026", owner: "Design Team", status: "Active", excerpt: "Use approved SVG/PNG files. Do not stretch, recolor, or add effects to the logo." },
];

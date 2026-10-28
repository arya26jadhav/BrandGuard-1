import type { Finding } from "@/types";

export const mockFindings: Finding[] = [
  {
    id: "finding-001", contentId: "content-001", type: "claim", start: 42, end: 67, bbox: null,
    severity: "critical", title: "Absolute skincare promise", reason: "The phrase promises a guaranteed result that is not supported by an approved product fact. It may mislead customers.",
    sourceId: "FACT-014", sourceVersion: 3, originalText: "100% clear skin", suggestedFix: "Helps support clearer-looking skin with regular use.",
    confidence: 0.97, aiGenerated: true, needsHumanReview: true, status: "open",
  },
  {
    id: "finding-002", contentId: "content-001", type: "claim", start: 84, end: 109, bbox: null,
    severity: "warning", title: "Unsupported speed claim", reason: "No approved evidence confirms that the face wash removes all acne overnight.",
    sourceId: "FACT-009", sourceVersion: 2, originalText: "Removes all acne overnight", suggestedFix: "Helps cleanse excess oil and impurities.",
    confidence: 0.93, aiGenerated: true, needsHumanReview: true, status: "open",
  },
  {
    id: "finding-003", contentId: "content-001", type: "rule", start: null, end: null, bbox: null,
    severity: "warning", title: "Required disclaimer missing", reason: "The skincare claims guideline requires the approved results disclaimer for this content type.",
    sourceId: "GUIDE-022", sourceVersion: 5, originalText: "Results may vary from person to person.", suggestedFix: "Add: Results may vary from person to person.",
    confidence: 1, aiGenerated: false, needsHumanReview: false, status: "open",
  },
  {
    id: "finding-004", contentId: "content-002", type: "image", start: null, end: null, bbox: [0.06, 0.08, 0.31, 0.18],
    severity: "warning", title: "Logo proportions look stretched", reason: "The uploaded logo does not match the approved asset proportions. Use the master logo without changing its aspect ratio.",
    sourceId: "ASSET-001", sourceVersion: 4, originalText: "GreenGlow logo", suggestedFix: "Replace with the approved GreenGlow horizontal logo.",
    confidence: 0.89, aiGenerated: true, needsHumanReview: true, status: "open",
  },
  {
    id: "finding-005", contentId: "content-002", type: "accessibility", start: null, end: null, bbox: [0.1, 0.55, 0.8, 0.12],
    severity: "info", title: "Text contrast may be too low", reason: "The text/background combination may not meet the 4.5:1 contrast target for regular text.",
    sourceId: "GUIDE-031", sourceVersion: 2, originalText: "Naturally fresh, every day", suggestedFix: "Use the approved deep-green text color on a light background.",
    confidence: 0.84, aiGenerated: true, needsHumanReview: true, status: "open",
  },
];

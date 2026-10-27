import type { AuditReport, AuditSummary, IssueType, StatItem } from "./types";

// Mock data. Box coordinates match components/audit/ShelfPlaceholder.tsx.
// Replace with FastAPI responses by setting NEXT_PUBLIC_API_URL.

export const SAMPLE_REPORT: AuditReport = {
  id: "aud_1042",
  storeName: "Al-Noor Mart, Clifton",
  createdAt: "2026-10-20T11:30:00+05:00",
  durationSec: 27,
  productsDetected: 86,
  isDemo: true,
  issues: [
    {
      id: "i1",
      type: "out_of_stock",
      severity: "high",
      shelf: 1,
      title: "Lays Masala: 3 facings empty",
      detail: "Expected 5 facings, found 2. Restock from the back room.",
      box: { x: 12, y: 6, w: 16, h: 24 },
    },
    {
      id: "i2",
      type: "out_of_stock",
      severity: "high",
      shelf: 2,
      title: "Pepsi 500ml: slot empty",
      detail: "No units detected in this slot.",
      box: { x: 20, y: 38, w: 12, h: 24 },
    },
    {
      id: "i3",
      type: "wrong_placement",
      severity: "medium",
      shelf: 2,
      title: "Sprite 1.5L in Pepsi block",
      detail: "The planogram expects Pepsi 500ml in this position.",
      box: { x: 52, y: 38, w: 12, h: 24 },
    },
    {
      id: "i4",
      type: "price_mismatch",
      severity: "medium",
      shelf: 3,
      title: "Surf Excel 1kg: tag shows Rs 450",
      detail: "System price is Rs 480. Update the shelf tag.",
      box: { x: 66, y: 94, w: 14, h: 6 },
    },
  ],
};

export const RECENT_AUDITS: ReadonlyArray<AuditSummary> = [
  { id: "aud_1042", storeName: "Al-Noor Mart, Clifton", createdAt: "2026-10-20T11:30:00+05:00", issueCount: 4 },
  { id: "aud_1041", storeName: "Al-Noor Mart, Gulshan", createdAt: "2026-10-20T10:05:00+05:00", issueCount: 7 },
  { id: "aud_1040", storeName: "Al-Noor Mart, DHA Phase 6", createdAt: "2026-10-19T17:40:00+05:00", issueCount: 2 },
  { id: "aud_1039", storeName: "Al-Noor Mart, Clifton", createdAt: "2026-10-19T12:15:00+05:00", issueCount: 5 },
  { id: "aud_1038", storeName: "Al-Noor Mart, Gulshan", createdAt: "2026-10-18T15:20:00+05:00", issueCount: 3 },
];

export const DASHBOARD_STATS: ReadonlyArray<StatItem> = [
  { label: "Audits this week", value: "48", hint: "+12 vs last week" },
  { label: "Stock-outs found", value: "131", hint: "Across 9 stores" },
  { label: "Price mismatches", value: "37", hint: "Tag vs system price" },
  { label: "Avg. audit time", value: "27s", hint: "Photo to report" },
];

export const ISSUE_BREAKDOWN: ReadonlyArray<{ type: IssueType; count: number }> = [
  { type: "out_of_stock", count: 131 },
  { type: "wrong_placement", count: 58 },
  { type: "price_mismatch", count: 37 },
];
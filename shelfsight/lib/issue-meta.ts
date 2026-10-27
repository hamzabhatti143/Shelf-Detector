import type { IssueType, Severity } from "./types";

interface IssueMeta {
  label: string;
  badge: string;
  box: string;
  dot: string;
}

export const ISSUE_META: Record<IssueType, IssueMeta> = {
  out_of_stock: {
    label: "Out of stock",
    badge: "bg-red-500/10 text-red-700 ring-red-500/30 dark:text-red-400",
    box: "border-red-500 bg-red-500/15 hover:bg-red-500/25",
    dot: "bg-red-500",
  },
  wrong_placement: {
    label: "Wrong placement",
    badge: "bg-amber-500/10 text-amber-700 ring-amber-500/30 dark:text-amber-400",
    box: "border-amber-500 bg-amber-500/15 hover:bg-amber-500/25",
    dot: "bg-amber-500",
  },
  price_mismatch: {
    label: "Price mismatch",
    badge: "bg-sky-500/10 text-sky-700 ring-sky-500/30 dark:text-sky-400",
    box: "border-sky-500 bg-sky-500/15 hover:bg-sky-500/25",
    dot: "bg-sky-500",
  },
};

export const ISSUE_TYPES: ReadonlyArray<IssueType> = ["out_of_stock", "wrong_placement", "price_mismatch"];

export const SEVERITY_CLASS: Record<Severity, string> = {
  high: "text-red-600 dark:text-red-400",
  medium: "text-amber-600 dark:text-amber-400",
  low: "text-zinc-500",
};
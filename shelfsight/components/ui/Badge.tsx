import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { ISSUE_META } from "@/lib/issue-meta";
import type { IssueType } from "@/lib/types";

interface BadgeProps {
  tone: IssueType | "neutral";
  children: ReactNode;
  className?: string;
}

const NEUTRAL =
  "bg-zinc-100 text-zinc-700 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700";

export function Badge({ tone, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset",
        tone === "neutral" ? NEUTRAL : ISSUE_META[tone].badge,
        className,
      )}
    >
      {children}
    </span>
  );
}
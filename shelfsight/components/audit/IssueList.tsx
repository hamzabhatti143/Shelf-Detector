import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";
import { REPORT_TEXT } from "@/lib/content";
import { ISSUE_META, SEVERITY_CLASS } from "@/lib/issue-meta";
import type { ShelfIssue } from "@/lib/types";

interface IssueListProps {
  issues: ShelfIssue[];
  activeIssueId: string | null;
  onSelectIssue: (id: string | null) => void;
}

export function IssueList({ issues, activeIssueId, onSelectIssue }: IssueListProps) {
  if (issues.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-lime-500/30 bg-lime-500/10 p-4 text-lime-800 dark:text-lime-300">
        <Icon name="check" />
        <p>{REPORT_TEXT.noIssues}</p>
      </div>
    );
  }

  return (
    <ol className="space-y-2" aria-label={REPORT_TEXT.issuesLabel}>
      {issues.map((issue, index) => {
        const meta = ISSUE_META[issue.type];
        const isActive = issue.id === activeIssueId;
        return (
          <li key={issue.id}>
            <button
              type="button"
              aria-pressed={isActive}
              onClick={() => onSelectIssue(issue.id)}
              onMouseEnter={() => onSelectIssue(issue.id)}
              onMouseLeave={() => onSelectIssue(null)}
              onFocus={() => onSelectIssue(issue.id)}
              onBlur={() => onSelectIssue(null)}
              className={cn(
                "w-full rounded-xl border p-4 text-left transition-colors",
                isActive
                  ? "border-lime-500 bg-lime-500/5"
                  : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700",
              )}
            >
              <div className="flex items-start gap-3">
                <span
                  className={cn(
                    "mt-0.5 grid size-6 shrink-0 place-items-center rounded-md text-xs font-semibold text-white",
                    meta.dot,
                  )}
                >
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{issue.title}</p>
                  <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{issue.detail}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Badge tone={issue.type}>{meta.label}</Badge>
                    <span className="font-mono text-xs text-zinc-500">
                      {REPORT_TEXT.shelf} {issue.shelf}
                    </span>
                    <span className={cn("text-xs font-medium", SEVERITY_CLASS[issue.severity])}>
                      {REPORT_TEXT.severity[issue.severity]}
                    </span>
                  </div>
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
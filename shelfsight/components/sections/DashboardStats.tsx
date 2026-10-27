import { cn } from "@/lib/cn";
import { DASHBOARD_TEXT } from "@/lib/content";
import { ISSUE_META } from "@/lib/issue-meta";
import { DASHBOARD_STATS, ISSUE_BREAKDOWN } from "@/lib/mock-data";

export function DashboardStats() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {DASHBOARD_STATS.map((stat) => (
        <div key={stat.label} className="rounded-2xl border border-zinc-200 p-5 dark:border-zinc-800">
          <p className="text-sm text-zinc-500">{stat.label}</p>
          <p className="mt-2 font-mono text-3xl font-semibold tracking-tight">{stat.value}</p>
          <p className="mt-1 text-xs text-zinc-500">{stat.hint}</p>
        </div>
      ))}
    </div>
  );
}

export function IssueBreakdown() {
  const max = Math.max(...ISSUE_BREAKDOWN.map((item) => item.count));

  return (
    <section className="rounded-2xl border border-zinc-200 p-5 dark:border-zinc-800">
      <h2 className="font-semibold">{DASHBOARD_TEXT.breakdownTitle}</h2>
      <ul className="mt-5 space-y-4">
        {ISSUE_BREAKDOWN.map((item) => (
          <li key={item.type}>
            <div className="flex justify-between text-sm">
              <span>{ISSUE_META[item.type].label}</span>
              <span className="font-mono text-zinc-500">{item.count}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
              <div
                className={cn("h-full rounded-full", ISSUE_META[item.type].dot)}
                style={{ width: `${(item.count / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
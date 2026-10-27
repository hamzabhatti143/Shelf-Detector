import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { DASHBOARD_TEXT } from "@/lib/content";
import { formatDateTime } from "@/lib/format";
import { RECENT_AUDITS } from "@/lib/mock-data";

export function RecentAudits() {
  return (
    <section className="rounded-2xl border border-zinc-200 dark:border-zinc-800">
      <h2 className="border-b border-zinc-200 px-5 py-4 font-semibold dark:border-zinc-800">
        {DASHBOARD_TEXT.recentTitle}
      </h2>
      <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
        {RECENT_AUDITS.map((audit) => (
          <li key={audit.id}>
            <Link
              href={`/audit/${audit.id}`}
              className="flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{audit.storeName}</p>
                <p className="mt-0.5 font-mono text-xs text-zinc-500">
                  {audit.id} · {formatDateTime(audit.createdAt)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <Badge tone="neutral">
                  {audit.issueCount} {DASHBOARD_TEXT.issuesSuffix}
                </Badge>
                <Icon name="arrow" className="size-4 text-zinc-400" />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
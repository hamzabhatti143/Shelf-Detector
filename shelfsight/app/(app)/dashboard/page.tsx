import type { Metadata } from "next";
import { ButtonLink } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { DashboardStats, IssueBreakdown } from "@/components/sections/DashboardStats";
import { RecentAudits } from "@/components/sections/RecentAudits";
import { DASHBOARD_TEXT } from "@/lib/content";

export const metadata: Metadata = { title: DASHBOARD_TEXT.title };

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{DASHBOARD_TEXT.title}</h1>
            <Badge tone="neutral">{DASHBOARD_TEXT.sampleBadge}</Badge>
          </div>
          <p className="mt-1 text-zinc-600 dark:text-zinc-400">{DASHBOARD_TEXT.subtitle}</p>
        </div>
        <ButtonLink href="/audit/new">{DASHBOARD_TEXT.newAudit}</ButtonLink>
      </div>

      <DashboardStats />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <RecentAudits />
        <IssueBreakdown />
      </div>
    </div>
  );
}
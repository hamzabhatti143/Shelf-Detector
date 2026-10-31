"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import { REPORT_TEXT } from "@/lib/content";
import { ISSUE_META, ISSUE_TYPES } from "@/lib/issue-meta";
import type { AuditReport } from "@/lib/types";
import { AnnotatedShelf } from "./AnnotatedShelf";
import { IssueList } from "./IssueList";
import { LiveVideoShelf } from "./LiveVideoShelf";

interface ReportViewProps {
  report: AuditReport;
  imageUrl: string | null;
}

type View = "live" | "best";

export function ReportView({ report, imageUrl }: ReportViewProps) {
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const isVideo = report.framesAnalyzed != null;
  const [view, setView] = useState<View>(isVideo ? "live" : "best");
  const [liveMissing, setLiveMissing] = useState(false);
  const showLive = isVideo && view === "live" && !liveMissing;

  return (
    <div className="space-y-6">
      {report.isDemo && (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
          {REPORT_TEXT.demoNotice}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {ISSUE_TYPES.map((type) => {
          const count = report.issues.filter((issue) => issue.type === type).length;
          return (
            <Badge key={type} tone={type}>
              {count} · {ISSUE_META[type].label}
            </Badge>
          );
        })}
        <span className="ml-1 font-mono text-xs text-zinc-500">
          {report.productsDetected} {REPORT_TEXT.products} · {report.durationSec}
          {REPORT_TEXT.secondsUnit}
          {report.priceTags?.length ? ` · ${report.priceTags.length} ${REPORT_TEXT.priceTagsLabel}` : ""}
        </span>
      </div>

      {isVideo && !liveMissing && (
        <div role="tablist" className="inline-flex rounded-lg border border-zinc-200 p-0.5 text-sm dark:border-zinc-800">
          {(
            [
              ["live", "Live detection"],
              ["best", "Best frame"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={view === id}
              onClick={() => setView(id)}
              className={cn(
                "rounded-md px-3 py-1.5 font-medium transition-colors",
                view === id
                  ? "bg-lime-400 text-zinc-900"
                  : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:items-start">
        <div>
          {isVideo && !liveMissing && (
            <div className={showLive ? "" : "hidden"}>
              <LiveVideoShelf auditId={report.id} onMissing={() => setLiveMissing(true)} />
            </div>
          )}
          {!showLive && (
            <AnnotatedShelf
              imageUrl={imageUrl}
              issues={report.issues}
              productBoxes={report.productBoxes}
              priceTags={report.priceTags}
              activeIssueId={activeIssueId}
              onSelectIssue={setActiveIssueId}
            />
          )}
        </div>
        <div className="space-y-2">
          {showLive && (
            <p className="text-xs text-zinc-500">Issues and prices below are from the best frame, not the frame playing.</p>
          )}
          <IssueList issues={report.issues} activeIssueId={activeIssueId} onSelectIssue={setActiveIssueId} />
        </div>
      </div>
    </div>
  );
}
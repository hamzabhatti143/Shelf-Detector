import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ReportView } from "@/components/audit/ReportView";
import { assetUrl, getAuditById } from "@/lib/api";
import { REPORT_TEXT } from "@/lib/content";
import { formatDateTime } from "@/lib/format";

// Static on purpose: reading params in generateMetadata is runtime data too.
export const metadata: Metadata = { title: REPORT_TEXT.reportTitle };

interface AuditPageProps {
  params: Promise<{ id: string }>;
}

function AuditSkeleton() {
  return (
    <div aria-busy="true" className="space-y-6">
      <p role="status" className="sr-only">
        {REPORT_TEXT.loading}
      </p>
      <div className="h-8 w-64 animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800" />
      <div className="aspect-[4/3] w-full animate-pulse rounded-2xl bg-zinc-100 dark:bg-zinc-800" />
    </div>
  );
}

async function AuditContent({ params }: AuditPageProps) {
  const { id } = await params;
  const report = await getAuditById(id);
  if (!report) notFound();

  return (
    <>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{report.storeName}</h1>
        <p className="mt-1 font-mono text-xs text-zinc-500">
          {report.id} · {formatDateTime(report.createdAt)}
        </p>
      </div>
      <ReportView report={report} imageUrl={report.imageUrl ? assetUrl(report.imageUrl) : null} />
    </>
  );
}

export default function AuditPage({ params }: AuditPageProps) {
  return (
    <div className="space-y-6">
      <Link
        href="/dashboard"
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        ← {REPORT_TEXT.back}
      </Link>
      <Suspense fallback={<AuditSkeleton />}>
        <AuditContent params={params} />
      </Suspense>
    </div>
  );
}
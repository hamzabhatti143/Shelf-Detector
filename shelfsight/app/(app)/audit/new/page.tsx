import type { Metadata } from "next";
import { AuditCapture } from "@/components/audit/AuditCapture";
import { UPLOADER_TEXT } from "@/lib/content";

export const metadata: Metadata = { title: UPLOADER_TEXT.title };

export default function NewAuditPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{UPLOADER_TEXT.title}</h1>
        <p className="mt-1 text-zinc-600 dark:text-zinc-400">{UPLOADER_TEXT.subtitle}</p>
      </div>
      <AuditCapture />
    </div>
  );
}
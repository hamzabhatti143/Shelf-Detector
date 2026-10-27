"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { AUDIT_MODES, MODE_TEXT } from "@/lib/content";
import type { AuditMode } from "@/lib/types";
import { ShelfUploader } from "./ShelfUploader";
import { VideoUploader } from "./VideoUploader";

const PANEL_ID = "capture-panel";

export function AuditCapture() {
  const [mode, setMode] = useState<AuditMode>("photo");

  return (
    <div className="space-y-6">
      <div
        role="tablist"
        aria-label={MODE_TEXT.tablistLabel}
        className="inline-flex rounded-xl border border-zinc-200 p-1 dark:border-zinc-800"
      >
        {AUDIT_MODES.map((item) => (
          <button
            key={item.id}
            id={`tab-${item.id}`}
            type="button"
            role="tab"
            aria-selected={mode === item.id}
            aria-controls={PANEL_ID}
            onClick={() => setMode(item.id)}
            className={cn(
              "rounded-lg px-5 py-2 text-sm font-medium transition-colors",
              mode === item.id
                ? "bg-lime-400 text-zinc-950"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={PANEL_ID} aria-labelledby={`tab-${mode}`}>
        {mode === "photo" ? <ShelfUploader /> : <VideoUploader />}
      </div>
    </div>
  );
}
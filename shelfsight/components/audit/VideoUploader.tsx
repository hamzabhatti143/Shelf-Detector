"use client";

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type SyntheticEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StoreSelect } from "@/components/ui/StoreSelect";
import { ApiError, analyzeVideo, assetUrl } from "@/lib/api";
import { cn } from "@/lib/cn";
import { MAX_VIDEO_BYTES, MAX_VIDEO_SECONDS, STORE_OPTIONS } from "@/lib/config";
import { VIDEO_TEXT } from "@/lib/content";
import { formatBytes, formatDuration } from "@/lib/format";
import type { AuditReport } from "@/lib/types";
import { ReportView } from "./ReportView";

type Phase = "idle" | "uploading" | "processing" | "done" | "error";

export function VideoUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [storeId, setStoreId] = useState<string>(STORE_OPTIONS[0].id);
  const [phase, setPhase] = useState<Phase>("idle");
  const [fraction, setFraction] = useState(0);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const recordInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const busy = phase === "uploading" || phase === "processing";
  const tooLong = duration !== null && duration > MAX_VIDEO_SECONDS;
  const message = error ?? (tooLong ? VIDEO_TEXT.errorDuration : null);

  function selectFile(selected: File | undefined) {
    if (!selected) return;
    if (!selected.type.startsWith("video/")) {
      setError(VIDEO_TEXT.errorType);
      return;
    }
    if (selected.size > MAX_VIDEO_BYTES) {
      setError(VIDEO_TEXT.errorSize);
      return;
    }
    setError(null);
    setReport(null);
    setDuration(null);
    setPhase("idle");
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  function handleMetadata(event: SyntheticEvent<HTMLVideoElement>) {
    const seconds = event.currentTarget.duration;
    if (Number.isFinite(seconds)) setDuration(seconds);
  }

  async function runAnalysis() {
    if (!file || tooLong) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setError(null);
    setFraction(0);
    setPhase("uploading");
    try {
      const result = await analyzeVideo(
        file,
        storeId,
        (progress) => {
          setPhase(progress.phase);
          setFraction(progress.fraction);
        },
        controller.signal,
      );
      setReport(result);
      setPhase("done");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof ApiError ? err.message : VIDEO_TEXT.errorGeneric);
      setPhase("error");
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setPhase("idle");
    setFraction(0);
  }

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setPreviewUrl(null);
    setDuration(null);
    setReport(null);
    setError(null);
    setFraction(0);
    setPhase("idle");
  }

  if (phase === "done" && report) {
    return (
      <div className="space-y-6">
        <ReportView report={report} imageUrl={report.imageUrl ? assetUrl(report.imageUrl) : null} />
        {report.framesAnalyzed ? (
          <p className="text-sm text-zinc-500">{VIDEO_TEXT.framesNote(report.framesAnalyzed)}</p>
        ) : null}
        <Button variant="secondary" onClick={reset}>
          {VIDEO_TEXT.another}
        </Button>
      </div>
    );
  }

  const progressLabel = phase === "uploading" ? VIDEO_TEXT.uploading : VIDEO_TEXT.processing;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="space-y-3">
        {previewUrl && file ? (
          <>
            <video
              key={previewUrl}
              src={previewUrl}
              controls
              muted
              playsInline
              preload="metadata"
              onLoadedMetadata={handleMetadata}
              aria-label={VIDEO_TEXT.previewLabel}
              className="aspect-video w-full rounded-2xl border border-zinc-200 bg-black object-contain dark:border-zinc-800"
            />
            <p className="font-mono text-xs text-zinc-500">
              {file.name} · {formatBytes(file.size)}
              {duration !== null ? ` · ${formatDuration(duration)}` : ""}
            </p>
          </>
        ) : (
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={cn(
              "flex aspect-video w-full flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-6 text-center transition-colors",
              dragging
                ? "border-lime-500 bg-lime-500/5"
                : "border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/50",
            )}
          >
            <span className="grid size-12 place-items-center rounded-full bg-lime-400/20 text-lime-600 dark:text-lime-400">
              <Icon name="upload" className="size-6" />
            </span>
            <div>
              <p className="font-medium">{VIDEO_TEXT.dropTitle}</p>
              <p className="mt-1 text-sm text-zinc-500">{VIDEO_TEXT.dropHint}</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              <Button onClick={() => recordInputRef.current?.click()}>
                <Icon name="camera" />
                {VIDEO_TEXT.record}
              </Button>
              <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                {VIDEO_TEXT.choose}
              </Button>
            </div>
          </div>
        )}

        <input
          ref={recordInputRef}
          type="file"
          accept="video/*"
          capture="environment"
          className="hidden"
          onChange={handleInputChange}
        />
        <input ref={fileInputRef} type="file" accept="video/*" className="hidden" onChange={handleInputChange} />
      </div>

      <div className="space-y-6">
        <StoreSelect id="video-store" value={storeId} onChange={setStoreId} disabled={busy} />

        <div className="flex flex-wrap gap-2">
          <Button size="lg" onClick={runAnalysis} disabled={!file || busy || tooLong}>
            {busy ? VIDEO_TEXT.analyzing : VIDEO_TEXT.analyze}
          </Button>
          {busy && (
            <Button variant="ghost" size="lg" onClick={cancel}>
              {VIDEO_TEXT.cancel}
            </Button>
          )}
          {file && !busy && (
            <Button variant="ghost" size="lg" onClick={reset}>
              {VIDEO_TEXT.reset}
            </Button>
          )}
        </div>

        {busy && <ProgressBar value={fraction} label={progressLabel} />}

        {message && (
          <p
            role="alert"
            className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-400"
          >
            {message}
          </p>
        )}
        <p role="status" aria-live="polite" className="sr-only">
          {busy ? progressLabel : ""}
        </p>

        <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          <p className="text-sm font-medium">{VIDEO_TEXT.tipsTitle}</p>
          <ul className="mt-3 space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
            {VIDEO_TEXT.tips.map((tip) => (
              <li key={tip} className="flex gap-2">
                <Icon name="check" className="mt-0.5 size-4 shrink-0 text-lime-500" />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
"use client";

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { analyzeShelf } from "@/lib/api";
import { cn } from "@/lib/cn";
import { MAX_UPLOAD_BYTES, STORE_OPTIONS } from "@/lib/config";
import { UPLOADER_TEXT } from "@/lib/content";
import type { AuditReport } from "@/lib/types";
import { AnnotatedShelf } from "./AnnotatedShelf";
import { ReportView } from "./ReportView";

type Phase = "idle" | "analyzing" | "done" | "error";

export function ShelfUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [storeId, setStoreId] = useState<string>(STORE_OPTIONS[0].id);
  const [phase, setPhase] = useState<Phase>("idle");
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function selectFile(selected: File | undefined) {
    if (!selected) return;
    if (!selected.type.startsWith("image/")) {
      setError(UPLOADER_TEXT.errorType);
      return;
    }
    if (selected.size > MAX_UPLOAD_BYTES) {
      setError(UPLOADER_TEXT.errorSize);
      return;
    }
    setError(null);
    setReport(null);
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

  async function runAnalysis() {
    if (!file) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setPhase("analyzing");
    setError(null);
    try {
      const result = await analyzeShelf(file, storeId, controller.signal);
      setReport(result);
      setPhase("done");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(UPLOADER_TEXT.errorGeneric);
      setPhase("error");
    }
  }

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setPreviewUrl(null);
    setReport(null);
    setError(null);
    setPhase("idle");
  }

  if (phase === "done" && report) {
    return (
      <div className="space-y-6">
        <ReportView report={report} imageUrl={previewUrl} />
        <Button variant="secondary" onClick={reset}>
          {UPLOADER_TEXT.another}
        </Button>
      </div>
    );
  }

  const isAnalyzing = phase === "analyzing";

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div>
        {previewUrl ? (
          <AnnotatedShelf imageUrl={previewUrl} issues={[]} scanning={isAnalyzing} />
        ) : (
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={cn(
              "flex aspect-[4/3] w-full flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-6 text-center transition-colors",
              dragging
                ? "border-lime-500 bg-lime-500/5"
                : "border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900/50",
            )}
          >
            <span className="grid size-12 place-items-center rounded-full bg-lime-400/20 text-lime-600 dark:text-lime-400">
              <Icon name="upload" className="size-6" />
            </span>
            <div>
              <p className="font-medium">{UPLOADER_TEXT.dropTitle}</p>
              <p className="mt-1 text-sm text-zinc-500">{UPLOADER_TEXT.dropHint}</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              <Button onClick={() => cameraInputRef.current?.click()}>
                <Icon name="camera" />
                {UPLOADER_TEXT.takePhoto}
              </Button>
              <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                {UPLOADER_TEXT.chooseFile}
              </Button>
            </div>
          </div>
        )}

        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleInputChange}
        />
        <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleInputChange} />
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="store" className="text-sm font-medium">
            {UPLOADER_TEXT.storeLabel}
          </label>
          <select
            id="store"
            value={storeId}
            onChange={(event) => setStoreId(event.target.value)}
            disabled={isAnalyzing}
            className="h-11 w-full rounded-lg border border-zinc-300 bg-white px-3 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          >
            {STORE_OPTIONS.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button size="lg" onClick={runAnalysis} disabled={!file || isAnalyzing}>
            {isAnalyzing ? UPLOADER_TEXT.analyzing : UPLOADER_TEXT.analyze}
          </Button>
          {file && (
            <Button variant="ghost" size="lg" onClick={reset} disabled={isAnalyzing}>
              {UPLOADER_TEXT.reset}
            </Button>
          )}
        </div>

        {error && (
          <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-400">
            {error}
          </p>
        )}
        <p role="status" aria-live="polite" className="sr-only">
          {isAnalyzing ? UPLOADER_TEXT.statusAnalyzing : ""}
        </p>

        <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          <p className="text-sm font-medium">{UPLOADER_TEXT.tipsTitle}</p>
          <ul className="mt-3 space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
            {UPLOADER_TEXT.tips.map((tip) => (
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
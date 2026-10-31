"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import {
  auditCamera,
  auditLiveCamera,
  startLiveCamera,
  stopLiveCamera,
  testCamera,
  type LiveBoxes,
} from "@/lib/api";
import { STORE_OPTIONS } from "@/lib/config";
import { ISSUE_META, ISSUE_TYPES } from "@/lib/issue-meta";
import type { ShelfIssue } from "@/lib/types";
import { CameraLivePanel } from "./CameraLivePanel";
import { IssueList } from "./IssueList";

type Busy = "idle" | "testing" | "starting" | "auditing";

export function CameraAudit() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [storeId, setStoreId] = useState(STORE_OPTIONS[0]?.id ?? "");
  const [busy, setBusy] = useState<Busy>("idle");
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [liveId, setLiveId] = useState<string | null>(null);
  const [issues, setIssues] = useState<ShelfIssue[]>([]);
  const [products, setProducts] = useState(0);
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const liveRef = useRef<string | null>(null);
  const issuesKey = useRef("");

  useEffect(() => {
    liveRef.current = liveId;
  }, [liveId]);
  useEffect(
    () => () => {
      abortRef.current?.abort();
      if (liveRef.current) stopLiveCamera(liveRef.current);
    },
    [],
  );
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  const handleData = useCallback((data: LiveBoxes) => {
    const next = data.issues ?? [];
    const key = JSON.stringify(next.map((issue) => [issue.type, issue.box]));
    if (key !== issuesKey.current) {
      issuesKey.current = key;
      setIssues(next);
    }
    setProducts(data.boxes?.length ?? 0);
  }, []);

  function begin(kind: Busy): AbortController {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(kind);
    setError(null);
    return controller;
  }

  function fail(cause: unknown) {
    if (cause instanceof DOMException && cause.name === "AbortError") return;
    setError(cause instanceof Error ? cause.message : "Something went wrong.");
  }

  async function onTest() {
    const controller = begin("testing");
    try {
      setPreview(URL.createObjectURL(await testCamera(url.trim(), controller.signal)));
    } catch (cause) {
      fail(cause);
    } finally {
      setBusy("idle");
    }
  }

  async function onStartLive() {
    const controller = begin("starting");
    try {
      setSavedId(null);
      issuesKey.current = "";
      setIssues([]);
      setLiveId((await startLiveCamera(url.trim(), controller.signal)).id);
    } catch (cause) {
      fail(cause);
    } finally {
      setBusy("idle");
    }
  }

  function onStopLive() {
    if (liveId) stopLiveCamera(liveId);
    setLiveId(null);
  }

  async function onAudit() {
    const controller = begin("auditing");
    try {
      if (liveId) {
        // keep the live view running; only save a record of this moment
        const report = await auditLiveCamera(liveId, storeId, controller.signal);
        setSavedId(report.id);
        setBusy("idle");
      } else {
        const report = await auditCamera(url.trim(), storeId, controller.signal);
        router.push(`/audit/${report.id}`);
      }
    } catch (cause) {
      fail(cause);
      setBusy("idle");
    }
  }

  const noUrl = url.trim().length === 0;
  const field =
    "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900";
  const secondary =
    "rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium transition-colors hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800";

  return (
    <div className="space-y-6">
      <div className="max-w-2xl space-y-4">
        <div className="space-y-2">
          <label htmlFor="camera-url" className="text-sm font-medium">
            Camera address
          </label>
          <input
            id="camera-url"
            type="text"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            disabled={liveId !== null}
            placeholder="rtsp://user:password@192.168.1.64:554/Streaming/Channels/101"
            autoComplete="off"
            spellCheck={false}
            className={`${field} font-mono disabled:opacity-60`}
          />
          <p className="text-xs text-zinc-500">
            RTSP or HTTP address of the camera. It is sent to your server to read the picture and is not saved.
          </p>
        </div>

        <div className="space-y-2">
          <label htmlFor="camera-store" className="text-sm font-medium">
            Store
          </label>
          <select id="camera-store" value={storeId} onChange={(event) => setStoreId(event.target.value)} className={field}>
            {STORE_OPTIONS.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap gap-3">
          {liveId ? (
            <button type="button" onClick={onStopLive} className={secondary}>
              Stop live view
            </button>
          ) : (
            <>
              <button type="button" onClick={onTest} disabled={busy !== "idle" || noUrl} className={secondary}>
                {busy === "testing" ? "Connecting…" : "Test connection"}
              </button>
              <button type="button" onClick={onStartLive} disabled={busy !== "idle" || noUrl} className={secondary}>
                {busy === "starting" ? "Starting…" : "Start live view"}
              </button>
            </>
          )}
          <button
            type="button"
            onClick={onAudit}
            disabled={busy !== "idle" || (noUrl && !liveId)}
            className="rounded-lg bg-lime-400 px-4 py-2 text-sm font-semibold text-zinc-900 transition-colors hover:bg-lime-300 disabled:opacity-50"
          >
            {busy === "auditing" ? "Saving…" : liveId ? "Save this audit" : "Audit now"}
          </button>
        </div>

        {error && (
          <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </p>
        )}
        {savedId && (
          <p className="rounded-lg border border-lime-500/30 bg-lime-500/10 px-4 py-3 text-sm">
            Saved.{" "}
            <Link href={`/audit/${savedId}`} className="font-medium underline">
              Open the saved report
            </Link>{" "}
            (it keeps one picture; the live view keeps running here).
          </p>
        )}
      </div>

      {liveId ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {ISSUE_TYPES.map((type) => (
              <Badge key={type} tone={type}>
                {issues.filter((issue) => issue.type === type).length} · {ISSUE_META[type].label}
              </Badge>
            ))}
            <span className="ml-1 font-mono text-xs text-zinc-500">{products} products</span>
          </div>
          <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:items-start">
            <CameraLivePanel id={liveId} onData={handleData} />
            <IssueList issues={issues} activeIssueId={activeIssueId} onSelectIssue={setActiveIssueId} />
          </div>
        </div>
      ) : (
        preview && (
          <div className="max-w-2xl space-y-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={preview} alt="Latest picture from the camera" className="block h-auto w-full rounded-2xl border border-zinc-200 dark:border-zinc-800" />
            <p className="text-xs text-zinc-500">Connection works. Use "Start live view" for the full live picture.</p>
          </div>
        )
      )}
    </div>
  );
}
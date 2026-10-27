import {
  MOCK_ANALYSIS_MS,
  MOCK_VIDEO_FRAMES,
  MOCK_VIDEO_PROCESS_MS,
  MOCK_VIDEO_TICK_MS,
  MOCK_VIDEO_UPLOAD_MS,
  STORE_OPTIONS,
  VIDEO_MAX_WAIT_MS,
  VIDEO_POLL_MS,
} from "./config";
import { VIDEO_TEXT } from "./content";
import { RECENT_AUDITS, SAMPLE_REPORT } from "./mock-data";
import type { AuditReport, VideoJob } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface VideoProgress {
  phase: "uploading" | "processing";
  fraction: number;
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function readDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

/** Turns a backend-relative path such as /v1/audits/x/image into an absolute URL. */
export function assetUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL ?? ""}${path}`;
}

/** Expected FastAPI contract: POST {API_URL}/v1/audits (multipart: image, store_id) -> AuditReport */
export async function analyzeShelf(file: File, storeId: string, signal?: AbortSignal): Promise<AuditReport> {
  if (!API_URL) {
    await wait(MOCK_ANALYSIS_MS, signal);
    const store = STORE_OPTIONS.find((s) => s.id === storeId);
    return {
      ...SAMPLE_REPORT,
      id: `aud_${Date.now()}`,
      createdAt: new Date().toISOString(),
      storeName: store?.name ?? SAMPLE_REPORT.storeName,
    };
  }

  const body = new FormData();
  body.append("image", file);
  body.append("store_id", storeId);
  const response = await fetch(`${API_URL}/v1/audits`, { method: "POST", body, signal });
  if (!response.ok) throw new Error(`Analysis failed (${response.status})`);
  return (await response.json()) as AuditReport;
}

export async function getAuditById(id: string): Promise<AuditReport | null> {
  if (!API_URL) {
    const summary = RECENT_AUDITS.find((audit) => audit.id === id);
    if (!summary) return null;
    return { ...SAMPLE_REPORT, id: summary.id, storeName: summary.storeName, createdAt: summary.createdAt };
  }

  const response = await fetch(`${API_URL}/v1/audits/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Failed to load audit (${response.status})`);
  return (await response.json()) as AuditReport;
}

// ---------------------------------------------------------------- video

/** POST {API_URL}/v1/video-audits (multipart: video, store_id) -> 202 VideoJob. XHR gives upload progress. */
function startVideoJob(
  file: File,
  storeId: string,
  onUploadProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<VideoJob> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/v1/video-audits`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onUploadProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as VideoJob);
      } else {
        reject(new ApiError(readDetail(xhr.response, VIDEO_TEXT.errorGeneric), xhr.status));
      }
    };
    xhr.onerror = () => reject(new ApiError(VIDEO_TEXT.errorNetwork));
    xhr.onabort = () => reject(new DOMException("Aborted", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });

    const body = new FormData();
    body.append("video", file);
    body.append("store_id", storeId);
    xhr.send(body);
  });
}

async function pollVideoJob(
  jobId: string,
  onUpdate: (job: VideoJob) => void,
  signal?: AbortSignal,
): Promise<VideoJob> {
  const deadline = Date.now() + VIDEO_MAX_WAIT_MS;
  while (Date.now() < deadline) {
    await wait(VIDEO_POLL_MS, signal);
    const response = await fetch(`${API_URL}/v1/video-audits/${encodeURIComponent(jobId)}`, {
      cache: "no-store",
      signal,
    });
    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(readDetail(body, VIDEO_TEXT.errorGeneric), response.status);
    }
    const job = body as VideoJob;
    onUpdate(job);
    if (job.status === "done" || job.status === "failed") return job;
  }
  throw new ApiError(VIDEO_TEXT.errorTimeout);
}

async function runTicks(totalMs: number, emit: (fraction: number) => void, signal?: AbortSignal): Promise<void> {
  const steps = Math.max(1, Math.round(totalMs / MOCK_VIDEO_TICK_MS));
  for (let i = 1; i <= steps; i += 1) {
    await wait(MOCK_VIDEO_TICK_MS, signal);
    emit(i / steps);
  }
}

async function mockAnalyzeVideo(
  storeId: string,
  onProgress: (progress: VideoProgress) => void,
  signal?: AbortSignal,
): Promise<AuditReport> {
  await runTicks(MOCK_VIDEO_UPLOAD_MS, (fraction) => onProgress({ phase: "uploading", fraction }), signal);
  await runTicks(MOCK_VIDEO_PROCESS_MS, (fraction) => onProgress({ phase: "processing", fraction }), signal);
  const store = STORE_OPTIONS.find((s) => s.id === storeId);
  return {
    ...SAMPLE_REPORT,
    id: `aud_${Date.now()}`,
    createdAt: new Date().toISOString(),
    storeName: store?.name ?? SAMPLE_REPORT.storeName,
    imageUrl: null,
    framesAnalyzed: MOCK_VIDEO_FRAMES,
  };
}

export async function analyzeVideo(
  file: File,
  storeId: string,
  onProgress: (progress: VideoProgress) => void,
  signal?: AbortSignal,
): Promise<AuditReport> {
  if (!API_URL) return mockAnalyzeVideo(storeId, onProgress, signal);

  const job = await startVideoJob(
    file,
    storeId,
    (fraction) => onProgress({ phase: "uploading", fraction }),
    signal,
  );
  onProgress({ phase: "processing", fraction: job.progress });
  const finished = await pollVideoJob(
    job.jobId,
    (update) => onProgress({ phase: "processing", fraction: update.progress }),
    signal,
  );
  if (finished.status === "failed" || !finished.auditId) {
    throw new ApiError(finished.error ?? VIDEO_TEXT.errorGeneric);
  }
  const report = await getAuditById(finished.auditId);
  if (!report) throw new ApiError(VIDEO_TEXT.errorMissing);
  return report;
}
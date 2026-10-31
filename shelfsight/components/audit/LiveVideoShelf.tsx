"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getTimeline, videoUrl } from "@/lib/api";
import type { VideoTimeline } from "@/lib/types";

interface LiveVideoShelfProps {
  auditId: string;
  onMissing?: () => void;
}

// OCR often keeps a stray piece of "Rs." in front of the number (".320", "s. 280"); show only the clean text.
function tagLabel(text: string): string {
  return text
    .replace(/^[\s.,]+(?=\d)/, "")
    .replace(/^[a-z]\.\s*(?=\d)/i, "")
    .trim();
}

/** A camera move as a complex similarity: z' = p * z + q (p = zoom + rotation, q = shift). */
interface Rel {
  pr: number;
  pi: number;
  qr: number;
  qi: number;
}
const IDENTITY: Rel = { pr: 1, pi: 0, qr: 0, qi: 0 };

function poseAt(samples: number[][], t: number): Rel {
  if (samples.length === 0) return IDENTITY;
  const toRel = (s: number[]): Rel => ({ pr: s[1], pi: s[2], qr: s[3], qi: s[4] });
  if (t <= samples[0][0]) return toRel(samples[0]);
  const last = samples[samples.length - 1];
  if (t >= last[0]) return toRel(last);
  let lo = 0;
  let hi = samples.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (samples[mid][0] <= t) lo = mid;
    else hi = mid;
  }
  const a = samples[lo];
  const b = samples[hi];
  const f = (t - a[0]) / (b[0] - a[0] || 1);
  const mix = (i: number) => a[i] + (b[i] - a[i]) * f;
  return { pr: mix(1), pi: mix(2), qr: mix(3), qi: mix(4) };
}

/** Where points of the frame seen at pose `from` are, in the frame seen at pose `to`. */
function relative(from: Rel, to: Rel): Rel {
  const d = from.pr * from.pr + from.pi * from.pi || 1;
  const pr = (to.pr * from.pr + to.pi * from.pi) / d;
  const pi = (to.pi * from.pr - to.pr * from.pi) / d;
  const rel = {
    pr,
    pi,
    qr: to.qr - (pr * from.qr - pi * from.qi),
    qi: to.qi - (pr * from.qi + pi * from.qr),
  };
  const zoom = Math.hypot(rel.pr, rel.pi);
  return zoom < 0.5 || zoom > 2 ? IDENTITY : rel; // a wild estimate is worse than no correction
}

/** Centre of a box (in %) moved by the camera. */
function mapCenter(rel: Rel, cx: number, cy: number, sw: number, sh: number): [number, number] {
  const x = (cx * sw) / 100;
  const y = (cy * sh) / 100;
  return [((rel.pr * x - rel.pi * y + rel.qr) / sw) * 100, ((rel.pr * y + rel.pi * x + rel.qi) / sh) * 100];
}

function nearestIndex(timeline: VideoTimeline, t: number): number {
  const frames = timeline.frames;
  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].t < t) lo = mid + 1;
    else hi = mid;
  }
  if (lo > 0 && Math.abs(frames[lo - 1].t - t) <= Math.abs(frames[lo].t - t)) lo -= 1;
  return lo;
}

/** One label per tag per frame. Frames without OCR borrow the text from the nearest OCR frame,
 *  but only for a tag that lands (after correcting for camera movement) on the same spot. */
function resolveLabels(timeline: VideoTimeline): string[][] {
  const frames = timeline.frames;
  const samples = timeline.motion?.samples ?? [];
  const sw = timeline.motion?.w ?? 1;
  const sh = timeline.motion?.h ?? 1;
  const ocrFrames = frames.map((f, i) => (f.ocr ? i : -1)).filter((i) => i >= 0);
  return frames.map((frame) => {
    const tags = frame.tags ?? [];
    if (frame.ocr) return tags.map((tag) => tagLabel(tag[4]) || "?");
    if (ocrFrames.length === 0) return tags.map(() => "");
    let nearest = ocrFrames[0];
    for (const k of ocrFrames) {
      if (Math.abs(frames[k].t - frame.t) < Math.abs(frames[nearest].t - frame.t)) nearest = k;
    }
    const source = frames[nearest];
    const rel = samples.length > 1 ? relative(poseAt(samples, source.t), poseAt(samples, frame.t)) : IDENTITY;
    return tags.map(([x, y, w, h]) => {
      let found = "";
      let bestDistance = Infinity;
      for (const [sx, sy, sbw, sbh, text] of source.tags ?? []) {
        const [mx, my] = mapCenter(rel, sx + sbw / 2, sy + sbh / 2, sw, sh);
        const distance = Math.hypot(mx - (x + w / 2), my - (y + h / 2));
        if (distance < bestDistance) {
          bestDistance = distance;
          found = tagLabel(text);
        }
      }
      return bestDistance <= Math.max(w, h) ? found : "";
    });
  });
}

export function LiveVideoShelf({ auditId, onMissing }: LiveVideoShelfProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [timeline, setTimeline] = useState<VideoTimeline | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const labels = useMemo(() => (timeline ? resolveLabels(timeline) : []), [timeline]);

  useEffect(() => {
    const controller = new AbortController();
    getTimeline(auditId, controller.signal)
      .then((data) => {
        if (data && data.frames.length > 0) {
          setTimeline(data);
          setStatus("ready");
        } else {
          setStatus("missing");
          onMissing?.();
        }
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setStatus("error");
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auditId]);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!timeline || !video || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const samples = timeline.motion?.samples ?? [];
    const sw = timeline.motion?.w ?? 1;
    const sh = timeline.motion?.h ?? 1;

    let raf = 0;
    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = video.clientWidth;
      const h = video.clientHeight;
      if (w === 0 || h === 0) return;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const now = video.currentTime;
      const index = nearestIndex(timeline, now);
      const frame = timeline.frames[index];
      // Boxes belong to the frame at frame.t; move them to where the camera is now.
      const rel = samples.length > 1 ? relative(poseAt(samples, frame.t), poseAt(samples, now)) : IDENTITY;
      const zoom = Math.hypot(rel.pr, rel.pi);
      const angle = Math.atan2(rel.pi, rel.pr);

      /** Strokes one moved box; returns its top-left corner (for labels). */
      const strokeBox = (x: number, y: number, bw: number, bh: number): [number, number] => {
        const [cx, cy] = mapCenter(rel, x + bw / 2, y + bh / 2, sw, sh);
        const px = (cx / 100) * w;
        const py = (cy / 100) * h;
        const pw = (bw / 100) * w * zoom;
        const ph = (bh / 100) * h * zoom;
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(angle);
        ctx.strokeRect(-pw / 2, -ph / 2, pw, ph);
        ctx.restore();
        return [px - pw / 2, py - ph / 2];
      };

      ctx.lineWidth = 2;
      ctx.strokeStyle = "rgba(163, 230, 53, 0.9)";
      for (const [x, y, bw, bh] of frame.boxes) strokeBox(x, y, bw, bh);

      ctx.lineWidth = 3;
      ctx.strokeStyle = "rgba(248, 113, 113, 0.95)";
      for (const [x, y, bw, bh] of frame.empties ?? []) strokeBox(x, y, bw, bh);
      ctx.lineWidth = 2;

      const tags = frame.tags ?? [];
      ctx.font = "600 10px ui-monospace, monospace";
      tags.forEach(([x, y, bw, bh], j) => {
        ctx.strokeStyle = "rgba(56, 189, 248, 0.95)";
        const [lx, ly] = strokeBox(x, y, bw, bh);
        const label = labels[index]?.[j] ?? "";
        if (label) {
          const lw = ctx.measureText(label).width + 8;
          ctx.fillStyle = "rgba(14, 165, 233, 0.95)";
          ctx.fillRect(lx, ly - 15, lw, 15);
          ctx.fillStyle = "#fff";
          ctx.fillText(label, lx + 4, ly - 4);
        }
      });

      const emptyCount = frame.empties?.length ?? 0;
      const text =
        `${frame.boxes.length} products` +
        (tags.length ? ` · ${tags.length} tags` : "") +
        (emptyCount ? ` · ${emptyCount} empty` : "") +
        ` · t ${now.toFixed(1)}s (detected ${frame.t.toFixed(1)}s)`;
      ctx.font = "600 12px ui-monospace, monospace";
      ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
      ctx.fillRect(8, 8, ctx.measureText(text).width + 16, 22);
      ctx.fillStyle = "#fff";
      ctx.fillText(text, 16, 23);
    };
    const loop = () => {
      draw();
      raf = requestAnimationFrame(loop);
    };
    const start = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(loop);
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      draw();
    };

    video.addEventListener("play", start);
    video.addEventListener("pause", stop);
    video.addEventListener("ended", stop);
    video.addEventListener("seeked", draw);
    video.addEventListener("loadeddata", draw);
    const observer = new ResizeObserver(draw);
    observer.observe(video);
    draw();
    if (!video.paused) start();

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      video.removeEventListener("play", start);
      video.removeEventListener("pause", stop);
      video.removeEventListener("ended", stop);
      video.removeEventListener("seeked", draw);
      video.removeEventListener("loadeddata", draw);
    };
  }, [timeline, labels]);

  if (status === "missing") return null;
  if (status === "error") {
    return (
      <p className="rounded-2xl border border-zinc-200 p-6 text-sm text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
        Live view could not be loaded.
      </p>
    );
  }

  const perSecond = timeline ? (timeline.frames.length / Math.max(timeline.duration, 1)).toFixed(1) : null;
  return (
    <div className="space-y-2">
      <div className="relative overflow-hidden rounded-2xl border border-zinc-200 bg-black dark:border-zinc-800">
        <video
          ref={videoRef}
          src={videoUrl(auditId)}
          controls
          playsInline
          muted
          loop
          preload="auto"
          className="block h-auto w-full"
        />
        <canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none absolute left-0 top-0 h-full w-full" />
      </div>
      {perSecond && (
        <p className="text-xs text-zinc-500">
          Detection runs about {perSecond} times per second; between those, boxes follow the camera movement. Prices
          are read on some frames only; a tag without a price was not read.
        </p>
      )}
    </div>
  );
}
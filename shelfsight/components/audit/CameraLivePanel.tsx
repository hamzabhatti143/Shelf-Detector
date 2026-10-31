"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getLiveBoxes, liveStreamUrl, type LiveBoxes } from "@/lib/api";

// OCR often keeps a stray piece of "Rs." in front of the number (".320", "s. 280"); show only the clean text.
function tagLabel(text: string): string {
  return text
    .replace(/^[\s.,]+(?=\d)/, "")
    .replace(/^[a-z]\.\s*(?=\d)/i, "")
    .trim();
}

interface CameraLivePanelProps {
  id: string;
  onData?: (data: LiveBoxes) => void;
}

export function CameraLivePanel({ id, onData }: CameraLivePanelProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const boxesRef = useRef<LiveBoxes | null>(null);
  const onDataRef = useRef(onData);
  const [ended, setEnded] = useState(false);

  useEffect(() => {
    onDataRef.current = onData;
  }, [onData]);

  const draw = useCallback(() => {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!img || !canvas || !ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = img.clientWidth;
    const h = img.clientHeight;
    if (w === 0 || h === 0) return;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const data = boxesRef.current;
    if (!data?.ready) return;

    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(163, 230, 53, 0.9)";
    for (const [x, y, bw, bh] of data.boxes ?? []) {
      ctx.strokeRect((x / 100) * w, (y / 100) * h, (bw / 100) * w, (bh / 100) * h);
    }

    ctx.font = "600 10px ui-monospace, monospace";
    for (const [x, y, bw, bh, text] of data.tags ?? []) {
      const px = (x / 100) * w;
      const py = (y / 100) * h;
      ctx.lineWidth = 2;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.95)";
      ctx.strokeRect(px, py, (bw / 100) * w, (bh / 100) * h);
      const label = tagLabel(text);
      if (label) {
        const lw = ctx.measureText(label).width + 8;
        ctx.fillStyle = "rgba(14, 165, 233, 0.95)";
        ctx.fillRect(px, py - 15, lw, 15);
        ctx.fillStyle = "#fff";
        ctx.fillText(label, px + 4, py - 4);
      }
    }

    (data.issues ?? []).forEach((issue, index) => {
      const px = (issue.box.x / 100) * w;
      const py = (issue.box.y / 100) * h;
      ctx.lineWidth = 3;
      ctx.strokeStyle = "rgba(248, 113, 113, 0.95)";
      ctx.strokeRect(px, py, (issue.box.w / 100) * w, (issue.box.h / 100) * h);
      ctx.fillStyle = "rgba(239, 68, 68, 0.95)";
      ctx.fillRect(px - 1, py - 1, 18, 16);
      ctx.fillStyle = "#fff";
      ctx.font = "700 11px ui-monospace, monospace";
      ctx.fillText(String(index + 1), px + 4, py + 11);
      ctx.font = "600 10px ui-monospace, monospace";
    });

    const text = `${data.boxes?.length ?? 0} products` + (data.tags?.length ? ` · ${data.tags.length} tags` : "");
    ctx.font = "600 12px ui-monospace, monospace";
    ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
    ctx.fillRect(8, 8, ctx.measureText(text).width + 16, 22);
    ctx.fillStyle = "#fff";
    ctx.fillText(text, 16, 23);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    const tick = async () => {
      try {
        const data = await getLiveBoxes(id, controller.signal);
        boxesRef.current = data;
        onDataRef.current?.(data);
        draw();
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setEnded(true);
        return;
      }
      if (!stopped) timer = setTimeout(tick, 700);
    };
    void tick();

    const img = imgRef.current;
    const observer = new ResizeObserver(draw);
    if (img) observer.observe(img);
    return () => {
      stopped = true;
      controller.abort();
      if (timer) clearTimeout(timer);
      observer.disconnect();
    };
  }, [id, draw]);

  if (ended) {
    return (
      <p className="rounded-2xl border border-zinc-200 p-6 text-sm text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
        The live view has ended. Start it again.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="relative overflow-hidden rounded-2xl border border-zinc-200 bg-black dark:border-zinc-800">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef}
          src={liveStreamUrl(id)}
          alt="Live camera"
          onLoad={draw}
          onError={() => setEnded(true)}
          className="block h-auto w-full"
        />
        <canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none absolute left-0 top-0 h-full w-full" />
      </div>
      <p className="text-xs text-zinc-500">
        Live picture. Boxes refresh about once a second; prices are read every few seconds and stay in place because the
        camera is fixed.
      </p>
    </div>
  );
}
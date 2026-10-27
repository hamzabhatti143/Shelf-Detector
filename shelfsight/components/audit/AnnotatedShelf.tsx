"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { REPORT_TEXT, SHELF_TEXT } from "@/lib/content";
import { formatPrice } from "@/lib/format";
import { ISSUE_META } from "@/lib/issue-meta";
import type { BoundingBox, PriceTagInfo, ShelfIssue } from "@/lib/types";
import { ShelfPlaceholder } from "./ShelfPlaceholder";

interface AnnotatedShelfProps {
  imageUrl: string | null;
  issues: ShelfIssue[];
  productBoxes?: BoundingBox[];
  priceTags?: PriceTagInfo[];
  activeIssueId?: string | null;
  onSelectIssue?: (id: string | null) => void;
  scanning?: boolean;
  className?: string;
}

export function AnnotatedShelf({
  imageUrl,
  issues,
  productBoxes = [],
  priceTags = [],
  activeIssueId = null,
  onSelectIssue,
  scanning = false,
  className,
}: AnnotatedShelfProps) {
  const reduceMotion = useReducedMotion();
  const hasActive = activeIssueId !== null;

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900",
        !imageUrl && "aspect-[4/3]",
        className,
      )}
    >
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl}
          alt={SHELF_TEXT.imageAlt}
          loading="lazy"
          decoding="async"
          className="block h-auto w-full"
        />
      ) : (
        <ShelfPlaceholder />
      )}

      {productBoxes.map((box, index) => (
        <div
          key={`p-${box.x}-${box.y}-${index}`}
          aria-hidden="true"
          className="pointer-events-none absolute rounded-sm border-2 border-lime-400/80"
          style={{ left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%` }}
        />
      ))}

      {priceTags.map((tag, index) => (
        <div
          key={`t-${tag.box.x}-${tag.box.y}-${index}`}
          aria-hidden="true"
          className="pointer-events-none absolute rounded-sm border-2 border-sky-400"
          style={{
            left: `${tag.box.x}%`,
            top: `${tag.box.y}%`,
            width: `${tag.box.w}%`,
            height: `${tag.box.h}%`,
          }}
        >
          <span className="absolute -top-4 left-0 rounded-sm bg-sky-500 px-1 text-[10px] font-semibold leading-4 text-white">
            {tag.text || REPORT_TEXT.priceUnknown}
          </span>
        </div>
      ))}

      {issues.map((issue, index) => {
        const meta = ISSUE_META[issue.type];
        const isActive = issue.id === activeIssueId;
        return (
          <motion.button
            key={issue.id}
            type="button"
            aria-label={`${meta.label}: ${issue.title}`}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: hasActive && !isActive ? 0.35 : 1, scale: 1 }}
            transition={{ duration: 0.25, delay: reduceMotion ? 0 : index * 0.08 }}
            onMouseEnter={() => onSelectIssue?.(issue.id)}
            onMouseLeave={() => onSelectIssue?.(null)}
            onFocus={() => onSelectIssue?.(issue.id)}
            onBlur={() => onSelectIssue?.(null)}
            onClick={() => onSelectIssue?.(issue.id)}
            style={{
              left: `${issue.box.x}%`,
              top: `${issue.box.y}%`,
              width: `${issue.box.w}%`,
              height: `${issue.box.h}%`,
            }}
            className={cn("absolute rounded-md border-2 transition-colors", meta.box, isActive && "z-10 ring-2 ring-white/80")}
          >
            <span
              className={cn(
                "absolute -left-0.5 -top-0.5 rounded-br-md px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white",
                meta.dot,
              )}
            >
              {index + 1}
            </span>
          </motion.button>
        );
      })}

      {scanning && !reduceMotion && (
        <motion.div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 h-24 border-b-2 border-lime-400 bg-gradient-to-b from-transparent to-lime-400/25"
          initial={{ top: "-25%" }}
          animate={{ top: "100%" }}
          transition={{ duration: 2.2, ease: "linear", repeat: Infinity }}
        />
      )}
    </div>
  );
}
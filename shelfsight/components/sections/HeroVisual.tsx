"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AnnotatedShelf } from "@/components/audit/AnnotatedShelf";
import { HERO } from "@/lib/content";
import { SAMPLE_REPORT } from "@/lib/mock-data";

export function HeroVisual() {
  const reduceMotion = useReducedMotion();

  return (
    <div className="relative">
      <AnnotatedShelf
        imageUrl={null}
        issues={SAMPLE_REPORT.issues}
        scanning
        className="shadow-2xl shadow-lime-500/10"
      />
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9, duration: 0.4 }}
        className="absolute -bottom-4 left-4 rounded-xl border border-zinc-200 bg-white px-4 py-2 font-mono text-xs shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
      >
        {SAMPLE_REPORT.issues.length} {HERO.chipSuffix} {SAMPLE_REPORT.durationSec}
        {HERO.chipUnit}
      </motion.div>
    </div>
  );
}
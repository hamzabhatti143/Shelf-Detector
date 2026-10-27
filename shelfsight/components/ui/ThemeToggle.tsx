"use client";

import { useEffect, useState } from "react";
import { THEME_STORAGE_KEY } from "@/lib/config";
import { COMMON_TEXT } from "@/lib/content";
import { Icon } from "./Icon";

export function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !isDark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next ? "dark" : "light");
    } catch {
      /* storage unavailable */
    }
    setIsDark(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? COMMON_TEXT.toggleToLight : COMMON_TEXT.toggleToDark}
      className="grid size-10 place-items-center rounded-lg text-zinc-600 transition-colors hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
    >
      <Icon name={isDark ? "sun" : "moon"} />
    </button>
  );
}
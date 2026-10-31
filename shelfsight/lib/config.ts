import type { IconName } from "@/components/ui/Icon";
import type { StoreOption } from "./types";

export const SITE = {
  name: "ShelfSight",
  tagline: "Shelf audits in 30 seconds, from one photo",
  description:
    "ShelfSight uses computer vision to detect out-of-stock items, wrong placement and price-tag mismatches from a single shelf photo. Built for FMCG sales teams and retailers.",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "https://shelfsight.vercel.app",
} as const;

export const NAV_LINKS: ReadonlyArray<{ label: string; href: string }> = [
  { label: "Features", href: "/#features" },
  { label: "How it works", href: "/#how-it-works" },
  { label: "FAQ", href: "/#faq" },
];

export const APP_NAV: ReadonlyArray<{
  label: string;
  href: string;
  icon: IconName;
  matchPrefix: string;
}> = [
  { label: "Dashboard", href: "/dashboard", icon: "dashboard", matchPrefix: "/dashboard" },
  { label: "New audit", href: "/audit/new", icon: "camera", matchPrefix: "/audit/new" },
  { label: "Live Camera", href: "/camera", icon: "camera", matchPrefix: "/camera" },
];

export const THEME_STORAGE_KEY = "shelfsight-theme";
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");document.documentElement.classList.toggle("dark",t!=="light")}catch(e){document.documentElement.classList.add("dark")}})();`;

export const MAX_UPLOAD_MB = 10;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;
export const MOCK_ANALYSIS_MS = 2600;

export const LOCALE = { locale: "en-GB", timeZone: "Asia/Karachi" } as const;

export const STORE_OPTIONS: ReadonlyArray<StoreOption> = [
  { id: "clifton", name: "Al-Noor Mart, Clifton" },
  { id: "gulshan", name: "Al-Noor Mart, Gulshan" },
  { id: "dha", name: "Al-Noor Mart, DHA Phase 6" },
];

export const MAX_VIDEO_MB = 100; // keep in sync with MAX_VIDEO_MB in backend/.env
export const MAX_VIDEO_BYTES = MAX_VIDEO_MB * 1024 * 1024;
export const MAX_VIDEO_SECONDS = 60;
export const VIDEO_POLL_MS = 1500;
export const VIDEO_MAX_WAIT_MS = 15 * 60 * 1000;

export const MOCK_VIDEO_UPLOAD_MS = 1000;
export const MOCK_VIDEO_PROCESS_MS = 3500;
export const MOCK_VIDEO_TICK_MS = 150;
export const MOCK_VIDEO_FRAMES = 12;
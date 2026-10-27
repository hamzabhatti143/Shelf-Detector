import type { IconName } from "@/components/ui/Icon";
import { MAX_UPLOAD_MB, MAX_VIDEO_MB, MAX_VIDEO_SECONDS } from "./config";
import type { AuditMode } from "./types";

export const COMMON_TEXT = {
  skipToContent: "Skip to content",
  toggleToLight: "Switch to light mode",
  toggleToDark: "Switch to dark mode",
  openMenu: "Open menu",
  closeMenu: "Close menu",
  demoLabel: "Demo mode",
} as const;

export const HERO = {
  eyebrow: "Retail shelf intelligence",
  title: "Shelf audits in 30 seconds. From one photo.",
  subtitle:
    "Snap a shelf. ShelfSight flags empty slots, misplaced products and wrong price tags, then sends the report to your manager.",
  primaryCta: "Try the demo",
  secondaryCta: "See how it works",
  trust: "Built for FMCG sales reps, distributors and marts in Pakistan.",
  chipSuffix: "issues found in",
  chipUnit: "s",
} as const;

export const FEATURES_SECTION = {
  id: "features",
  title: "Three problems. One photo.",
  subtitle: "The shelf problems that cost retailers sales every day, caught before the customer walks away.",
} as const;

export const FEATURES: ReadonlyArray<{
  icon: IconName;
  title: string;
  description: string;
  example: string;
}> = [
  {
    icon: "alert",
    title: "Out-of-stock detection",
    description: "Finds empty slots and thin facings so restocking happens before the sale is lost.",
    example: "Shelf 1 · Lays Masala · 3 facings empty",
  },
  {
    icon: "swap",
    title: "Wrong placement",
    description: "Compares what is on the shelf with the planogram and flags products in the wrong spot.",
    example: "Shelf 2 · Sprite 1.5L in Pepsi slot",
  },
  {
    icon: "tag",
    title: "Price-tag mismatch",
    description: "Reads shelf tags with OCR and checks them against your price list.",
    example: "Shelf 3 · Tag Rs 450 · system Rs 480",
  },
];

export const HOW_IT_WORKS = {
  id: "how-it-works",
  title: "From photo to report",
  steps: [
    { title: "Photograph the shelf", description: "Use your phone camera. A capture guide keeps the angle and light usable." },
    { title: "AI reads the shelf", description: "Products, empty gaps and price tags are detected, then matched to your SKUs." },
    { title: "Compare with the plan", description: "Results are checked against your planogram and price list." },
    { title: "Act on the report", description: "Issues are ranked by severity and sent to the dashboard and WhatsApp." },
  ],
} as const;

export const FAQ_SECTION = { id: "faq", title: "Questions" } as const;

export const FAQ_ITEMS: ReadonlyArray<{ question: string; answer: string }> = [
  {
    question: "How long does an audit take?",
    answer: "About 30 seconds from photo to report.",
  },
  {
    question: "Do I need to retrain the model for every new product?",
    answer:
      "No. Products are recognised with embeddings and vector search, so adding a new SKU takes 5 to 10 reference photos instead of a retraining run.",
  },
  {
    question: "Does it work with local products and Urdu price tags?",
    answer:
      "That is the design goal. Detection is fine-tuned on local shelf photos and tag reading is built for mixed Urdu and English prices.",
  },
  {
    question: "Can reports be sent on WhatsApp?",
    answer: "Yes. Reports go to the dashboard and can be forwarded to the store manager on WhatsApp.",
  },
];

export const CTA = {
  title: "See your first shelf report",
  subtitle: "Upload any shelf photo and watch the audit run.",
  button: "Try the demo",
} as const;

export const FOOTER = {
  rights: "All rights reserved.",
  built: "Built with Next.js, FastAPI and YOLO11.",
} as const;

export const DASHBOARD_TEXT = {
  title: "Dashboard",
  subtitle: "Shelf health across your stores this week.",
  sampleBadge: "Sample data",
  newAudit: "New audit",
  breakdownTitle: "Issues by type",
  recentTitle: "Recent audits",
  issuesSuffix: "issues",
} as const;

export const UPLOADER_TEXT = {
  title: "New shelf audit",
  subtitle: "Photograph one shelf bay. Results in about 30 seconds.",
  dropTitle: "Drop a shelf photo here",
  dropHint: `JPG, PNG or WebP, up to ${MAX_UPLOAD_MB} MB`,
  takePhoto: "Take photo",
  chooseFile: "Choose file",
  storeLabel: "Store",
  analyze: "Analyze shelf",
  analyzing: "Analyzing shelf...",
  statusAnalyzing: "Analyzing your shelf photo",
  reset: "Remove photo",
  another: "Audit another shelf",
  errorType: "Please choose an image file.",
  errorSize: `That image is larger than ${MAX_UPLOAD_MB} MB.`,
  errorGeneric: "Analysis failed. Please try again.",
  tipsTitle: "For best results",
  tips: [
    "Stand straight on, about one metre from the shelf.",
    "Capture one shelf bay per photo.",
    "Avoid glare from lights and fridge doors.",
    "Keep price tags in frame and in focus.",
  ],
  previewAlt: "Selected shelf photo",
} as const;

export const SHELF_TEXT = {
  imageAlt: "Shelf photo with detected issues highlighted",
  placeholderLabel: "Illustration of a retail shelf with highlighted issues",
} as const;

export const REPORT_TEXT = {
  reportTitle: "Audit",
  back: "Back to dashboard",
  loading: "Loading report...",
  demoNotice: "Demo mode: detections shown are sample data. Connect the FastAPI model to see real results.",
  issuesLabel: "Detected issues",
  noIssues: "No issues found on this shelf.",
  shelf: "Shelf",
  products: "products",
  secondsUnit: "s",
  severity: { high: "High", medium: "Medium", low: "Low" },
  priceUnknown: "?",
  priceTagsLabel: "price tags read",
} as const;

export const MODE_TEXT = { tablistLabel: "Audit type" } as const;

export const AUDIT_MODES: ReadonlyArray<{ id: AuditMode; label: string }> = [
  { id: "photo", label: "Photo" },
  { id: "video", label: "Video" },
];

export const VIDEO_TEXT = {
  dropTitle: "Drop a shelf video here",
  dropHint: `MP4, MOV or WebM, up to ${MAX_VIDEO_MB} MB and ${MAX_VIDEO_SECONDS} seconds`,
  record: "Record video",
  choose: "Choose file",
  analyze: "Analyze video",
  analyzing: "Analyzing video...",
  reset: "Remove video",
  another: "Audit another video",
  cancel: "Cancel",
  uploading: "Uploading video",
  processing: "Reading frames and finding empty slots",
  previewLabel: "Selected shelf video",
  errorType: "Please choose a video file.",
  errorSize: `That video is larger than ${MAX_VIDEO_MB} MB.`,
  errorDuration: `Videos must be ${MAX_VIDEO_SECONDS} seconds or shorter.`,
  errorGeneric: "Video analysis failed. Please try again.",
  errorNetwork: "Could not reach the server. Check your connection.",
  errorTimeout: "Analysis is taking too long. Try a shorter video.",
  errorMissing: "The report could not be loaded.",
  tipsTitle: "For best results",
  tips: [
    "Hold the phone steady and pan slowly along one shelf bay.",
    "Stay about one metre from the shelf and keep it in focus.",
    "Pause for a second on any gap so the empty slot is clear.",
    "Avoid glare from lights and fridge doors.",
  ],
  framesNote: (count: number) =>
    `Showing the best of ${count} frames sampled from the video.`,
} as const;
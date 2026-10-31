export type IssueType = "out_of_stock" | "wrong_placement" | "price_mismatch";
export type Severity = "high" | "medium" | "low";

/** All values are percentages (0-100) of the image width/height. */
export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PriceTagInfo {
  box: BoundingBox;
  text: string;
  price: number | null;
  confidence: number;
}

export interface ShelfIssue {
  id: string;
  type: IssueType;
  severity: Severity;
  title: string;
  detail: string;
  shelf: number;
  box: BoundingBox;
}

export interface AuditReport {
  id: string;
  storeName: string;
  createdAt: string;
  durationSec: number;
  productsDetected: number;
  issues: ShelfIssue[];
  isDemo: boolean;
  imageUrl?: string | null;
  framesAnalyzed?: number | null;
  productBoxes?: BoundingBox[];
  priceTags?: PriceTagInfo[];
}

export type AuditMode = "photo" | "video";
export type VideoJobStatus = "queued" | "processing" | "done" | "failed";

export interface VideoJob {
  jobId: string;
  status: VideoJobStatus;
  progress: number;
  auditId: string | null;
  error: string | null;
}

export interface AuditSummary {
  id: string;
  storeName: string;
  createdAt: string;
  issueCount: number;
}

export interface StatItem {
  label: string;
  value: string;
  hint: string;
}

export interface StoreOption {
  id: string;
  name: string;
}

export interface VideoTimelineFrame {
  t: number;
  /** [x, y, w, h] in % of the frame */
  boxes: [number, number, number, number][];
  /** [x, y, w, h, text] price tags; text is only filled on frames where OCR ran */
  tags?: [number, number, number, number, string][];
  /** [x, y, w, h] empty slots found on this frame */
  empties?: [number, number, number, number][];
  ocr?: boolean;
}

export interface VideoMotion {
  w: number;
  h: number;
  /** [seconds, a, b, tx, ty]: cumulative camera motion, z' = (a + bi) z + (tx + ty i) in pixels of a w x h copy */
  samples: number[][];
}

export interface VideoTimeline {
  width: number;
  height: number;
  duration: number;
  frames: VideoTimelineFrame[];
  motion?: VideoMotion;
}
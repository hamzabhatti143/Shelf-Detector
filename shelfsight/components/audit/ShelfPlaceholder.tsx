import { SHELF_TEXT } from "@/lib/content";

// SVG viewBox is 400x300 so percentages in mock issues map 1:1 (x*4, y*3).
const ROW_TOPS = [18, 114, 210] as const;
const ROW_HEIGHT = 72;
const WIDTHS = [32, 28, 36, 30] as const;
const FILLS = [
  "fill-zinc-300 dark:fill-zinc-700",
  "fill-zinc-400/70 dark:fill-zinc-600",
  "fill-emerald-300/70 dark:fill-emerald-800/70",
  "fill-rose-300/70 dark:fill-rose-900/70",
  "fill-stone-300 dark:fill-stone-700",
  "fill-sky-300/70 dark:fill-sky-900/70",
] as const;
// Empty slots (x ranges) that match the out_of_stock sample issues.
const GAPS: Record<number, ReadonlyArray<readonly [number, number]>> = {
  0: [[48, 112]],
  1: [[80, 128]],
};
const TAG_XS = [12, 90, 170, 270, 340] as const;

interface ProductRect {
  x: number;
  w: number;
  fill: string;
}

function buildRow(row: number): ProductRect[] {
  const items: ProductRect[] = [];
  let x = 8;
  let i = row * 3;
  while (x < 392) {
    const w = WIDTHS[i % WIDTHS.length];
    if (x + w > 392) break;
    const blocked = (GAPS[row] ?? []).some(([start, end]) => x < end && x + w > start);
    if (!blocked) items.push({ x, w, fill: FILLS[i % FILLS.length] });
    x += w + 4;
    i += 1;
  }
  return items;
}

export function ShelfPlaceholder() {
  return (
    <svg
      viewBox="0 0 400 300"
      className="size-full"
      role="img"
      aria-label={SHELF_TEXT.placeholderLabel}
      preserveAspectRatio="xMidYMid slice"
    >
      {ROW_TOPS.map((top, row) => (
        <g key={top}>
          {buildRow(row).map((item) => (
            <rect key={item.x} x={item.x} y={top} width={item.w} height={ROW_HEIGHT} rx={3} className={item.fill} />
          ))}
          <rect x={0} y={top + ROW_HEIGHT} width={400} height={6} className="fill-zinc-400 dark:fill-zinc-600" />
          {TAG_XS.map((x) => (
            <rect
              key={x}
              x={x}
              y={top + ROW_HEIGHT + 8}
              width={32}
              height={8}
              rx={1}
              className="fill-white dark:fill-zinc-200"
            />
          ))}
        </g>
      ))}
      {/* Misplaced product (wrong_placement sample) */}
      <rect x={208} y={114} width={48} height={72} rx={3} className="fill-amber-400/80 dark:fill-amber-500/60" />
    </svg>
  );
}
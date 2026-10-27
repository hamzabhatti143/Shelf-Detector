import { cn } from "@/lib/cn";

interface ProgressBarProps {
  /** 0 to 1 */
  value: number;
  label: string;
  className?: string;
}

export function ProgressBar({ value, label, className }: ProgressBarProps) {
  const percent = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="font-mono text-zinc-500">{percent}%</span>
      </div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800"
      >
        <div
          className="h-full rounded-full bg-lime-400 transition-[width] duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
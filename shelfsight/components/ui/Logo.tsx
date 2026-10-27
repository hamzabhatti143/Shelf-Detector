import { SITE } from "@/lib/config";
import { cn } from "@/lib/cn";

interface LogoProps {
  className?: string;
}

export function Logo({ className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-lg font-semibold tracking-tight", className)}>
      <svg
        viewBox="0 0 24 24"
        className="size-6 text-lime-500"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4 8V5a1 1 0 011-1h3 M16 4h3a1 1 0 011 1v3 M20 16v3a1 1 0 01-1 1h-3 M8 20H5a1 1 0 01-1-1v-3 M7 12h10" />
      </svg>
      {SITE.name}
    </span>
  );
}
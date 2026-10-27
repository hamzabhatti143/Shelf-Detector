const PATHS = {
  sun: "M12 8a4 4 0 100 8 4 4 0 000-8z M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4",
  moon: "M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z",
  camera: "M4 8h3l2-3h6l2 3h3v11H4z M12 11a3.5 3.5 0 100 7 3.5 3.5 0 000-7z",
  dashboard: "M4 4h7v7H4z M13 4h7v4h-7z M13 10h7v10h-7z M4 13h7v7H4z",
  alert: "M12 3l10 18H2z M12 10v5 M12 18v.5",
  tag: "M3 12V3h9l9 9-9 9z M7.5 7.5h.01",
  swap: "M7 4v16 M3 8l4-4 4 4 M17 20V4 M13 16l4 4 4-4",
  upload: "M12 16V4 M7 9l5-5 5 5 M4 20h16",
  arrow: "M5 12h14 M13 6l6 6-6 6",
  check: "M5 13l4 4L19 7",
  menu: "M4 7h16 M4 12h16 M4 17h16",
  close: "M6 6l12 12 M18 6L6 18",
  plus: "M12 5v14 M5 12h14",
} as const;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  className?: string;
}

export function Icon({ name, className = "size-5" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
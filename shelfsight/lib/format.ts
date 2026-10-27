import { LOCALE } from "./config";

const formatter = new Intl.DateTimeFormat(LOCALE.locale, {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: LOCALE.timeZone,
});

export function formatDateTime(iso: string): string {
  return formatter.format(new Date(iso));
}

export function formatBytes(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  if (mb < 1) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${mb.toFixed(1)} MB`;
}

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, "0")}`;
}

export function formatPrice(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
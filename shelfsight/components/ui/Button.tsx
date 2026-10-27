import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface StyleOptions {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
}

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:pointer-events-none disabled:opacity-50";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-lime-400 text-zinc-950 hover:bg-lime-300",
  secondary:
    "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800",
  ghost: "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
};

export function buttonStyles({ variant = "primary", size = "md", className }: StyleOptions): string {
  return cn(BASE, VARIANTS[variant], SIZES[size], className);
}

type ButtonProps = StyleOptions & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className">;

export function Button({ variant, size, className, type = "button", ...rest }: ButtonProps) {
  return <button type={type} className={buttonStyles({ variant, size, className })} {...rest} />;
}

type ButtonLinkProps = StyleOptions & Omit<ComponentPropsWithoutRef<typeof Link>, "className">;

export function ButtonLink({ variant, size, className, ...rest }: ButtonLinkProps) {
  return <Link className={buttonStyles({ variant, size, className })} {...rest} />;
}
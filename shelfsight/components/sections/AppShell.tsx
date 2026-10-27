import Link from "next/link";
import { Suspense, type ReactNode } from "react";
import { Logo } from "@/components/ui/Logo";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { COMMON_TEXT } from "@/lib/content";
import { AppNav, AppNavStatic } from "./AppNav";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh flex-col gap-8 border-r border-zinc-200 p-5 lg:flex dark:border-zinc-800">
        <Link href="/" aria-label="Home">
          <Logo />
        </Link>
        <Suspense fallback={<AppNavStatic variant="sidebar" />}>
          <AppNav variant="sidebar" />
        </Suspense>
        <div className="mt-auto flex items-center justify-between">
          <ThemeToggle />
          <span className="font-mono text-xs text-zinc-500">{COMMON_TEXT.demoLabel}</span>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col pb-24 lg:pb-0">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-zinc-200 bg-white/80 px-4 backdrop-blur lg:hidden dark:border-zinc-800 dark:bg-zinc-950/80">
          <Link href="/" aria-label="Home">
            <Logo />
          </Link>
          <ThemeToggle />
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-10">
          {children}
        </main>
      </div>

      <Suspense fallback={<AppNavStatic variant="mobile" />}>
        <AppNav variant="mobile" />
      </Suspense>
    </div>
  );
}
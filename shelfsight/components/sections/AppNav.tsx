"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";
import { APP_NAV } from "@/lib/config";

type NavVariant = "sidebar" | "mobile";

interface NavListProps {
  variant: NavVariant;
  pathname: string;
}

function NavList({ variant, pathname }: NavListProps) {
  const isActive = (prefix: string) => pathname.startsWith(prefix);

  if (variant === "sidebar") {
    return (
      <nav aria-label="App" className="flex flex-col gap-1">
        {APP_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive(item.matchPrefix) ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive(item.matchPrefix)
                ? "bg-lime-400/15 text-lime-800 dark:text-lime-300"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800",
            )}
          >
            <Icon name={item.icon} />
            {item.label}
          </Link>
        ))}
      </nav>
    );
  }

  return (
    <nav
      aria-label="App mobile"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-zinc-200 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden dark:border-zinc-800 dark:bg-zinc-950/90"
    >
      {APP_NAV.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={isActive(item.matchPrefix) ? "page" : undefined}
          className={cn(
            "flex flex-1 flex-col items-center gap-1 py-2.5 text-xs font-medium",
            isActive(item.matchPrefix) ? "text-lime-700 dark:text-lime-400" : "text-zinc-500",
          )}
        >
          <Icon name={item.icon} />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

interface AppNavProps {
  variant: NavVariant;
}

/** Reads the URL, so it must sit inside <Suspense>. */
export function AppNav({ variant }: AppNavProps) {
  const pathname = usePathname();
  return <NavList variant={variant} pathname={pathname} />;
}

/** Same links with nothing highlighted. Used as the Suspense fallback. */
export function AppNavStatic({ variant }: AppNavProps) {
  return <NavList variant={variant} pathname="" />;
}
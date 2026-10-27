import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { NAV_LINKS, SITE } from "@/lib/config";
import { FOOTER } from "@/lib/content";

export function Footer() {
  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <Logo />
          <p className="text-sm text-zinc-500">{FOOTER.built}</p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-600 dark:text-zinc-400">
          {NAV_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-zinc-900 dark:hover:text-zinc-100">
              {link.label}
            </Link>
          ))}
        </nav>
        <p className="text-sm text-zinc-500">
          © 2026 {SITE.name}. {FOOTER.rights}
        </p>
      </div>
    </footer>
  );
}
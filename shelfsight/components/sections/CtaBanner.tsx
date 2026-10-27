import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { CTA } from "@/lib/content";

export function CtaBanner() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6 lg:pb-24">
      <div className="rounded-3xl bg-zinc-950 px-6 py-14 text-center text-zinc-50 dark:border dark:border-zinc-800 dark:bg-zinc-900 sm:px-12">
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">{CTA.title}</h2>
        <p className="mx-auto mt-3 max-w-xl text-zinc-400">{CTA.subtitle}</p>
        <ButtonLink href="/audit/new" size="lg" className="mt-8">
          {CTA.button}
          <Icon name="arrow" />
        </ButtonLink>
      </div>
    </section>
  );
}
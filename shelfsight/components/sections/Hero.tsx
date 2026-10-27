import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { HERO } from "@/lib/content";
import { HeroVisual } from "./HeroVisual";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div aria-hidden="true" className="hero-glow absolute inset-0 -z-10" />
      <div aria-hidden="true" className="bg-grid absolute inset-0 -z-10" />

      <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-lime-600 dark:text-lime-400">
            {HERO.eyebrow}
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
            {HERO.title}
          </h1>
          <p className="mt-5 max-w-xl text-lg text-zinc-600 dark:text-zinc-400">{HERO.subtitle}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/audit/new" size="lg">
              {HERO.primaryCta}
              <Icon name="arrow" />
            </ButtonLink>
            <ButtonLink href="/#how-it-works" variant="secondary" size="lg">
              {HERO.secondaryCta}
            </ButtonLink>
          </div>
          <p className="mt-6 text-sm text-zinc-500">{HERO.trust}</p>
        </div>

        <HeroVisual />
      </div>
    </section>
  );
}
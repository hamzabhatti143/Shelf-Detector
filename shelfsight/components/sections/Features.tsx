import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/ui/Reveal";
import { FEATURES, FEATURES_SECTION } from "@/lib/content";

export function Features() {
  return (
    <section id={FEATURES_SECTION.id} className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
      <Reveal>
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">{FEATURES_SECTION.title}</h2>
        <p className="mt-3 max-w-2xl text-zinc-600 dark:text-zinc-400">{FEATURES_SECTION.subtitle}</p>
      </Reveal>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {FEATURES.map((feature, index) => (
          <Reveal key={feature.title} delay={index * 0.08}>
            <article className="h-full rounded-2xl border border-zinc-200 p-6 dark:border-zinc-800">
              <span className="grid size-10 place-items-center rounded-lg bg-lime-400/15 text-lime-600 dark:text-lime-400">
                <Icon name={feature.icon} />
              </span>
              <h3 className="mt-5 text-lg font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{feature.description}</p>
              <p className="mt-5 rounded-lg bg-zinc-100 px-3 py-2 font-mono text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
                {feature.example}
              </p>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
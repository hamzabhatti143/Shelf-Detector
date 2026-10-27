import { Reveal } from "@/components/ui/Reveal";
import { HOW_IT_WORKS } from "@/lib/content";

export function HowItWorks() {
  return (
    <section
      id={HOW_IT_WORKS.id}
      className="border-y border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/40"
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">{HOW_IT_WORKS.title}</h2>
        </Reveal>
        <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_IT_WORKS.steps.map((step, index) => (
            <li key={step.title}>
              <Reveal delay={index * 0.08}>
                <span className="font-mono text-sm text-lime-600 dark:text-lime-400">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3 className="mt-2 text-lg font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{step.description}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
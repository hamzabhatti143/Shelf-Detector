import { Icon } from "@/components/ui/Icon";
import { FAQ_ITEMS, FAQ_SECTION } from "@/lib/content";

export function Faq() {
  return (
    <section id={FAQ_SECTION.id} className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:py-24">
      <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">{FAQ_SECTION.title}</h2>
      <div className="mt-8 divide-y divide-zinc-200 border-y border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
        {FAQ_ITEMS.map((item) => (
          <details key={item.question} className="group py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium [&::-webkit-details-marker]:hidden">
              {item.question}
              <Icon name="plus" className="size-5 shrink-0 transition-transform group-open:rotate-45" />
            </summary>
            <p className="mt-3 text-zinc-600 dark:text-zinc-400">{item.answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
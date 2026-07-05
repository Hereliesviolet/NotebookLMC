import { Collapsible } from "@/components/ui/collapsible";
import type { StudioFaqContent } from "@/lib/types";

export function StudioFaqView({ content }: { content: StudioFaqContent }) {
  if (content.items.length === 0) {
    return <p className="text-sm text-muted-foreground">Keine Fragen gefunden.</p>;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {content.items.map((item, index) => (
        <Collapsible
          key={index}
          className="rounded-md border border-border px-4 py-3"
          triggerClassName="w-full justify-between text-left"
          trigger={() => <span className="pr-2 text-sm font-medium text-foreground">{item.question}</span>}
        >
          <p className="text-sm leading-relaxed text-muted-foreground">{item.answer}</p>
        </Collapsible>
      ))}
    </div>
  );
}

import type { StudioTimelineContent } from "@/lib/types";

export function StudioTimelineView({ content }: { content: StudioTimelineContent }) {
  if (content.events.length === 0) {
    return <p className="text-sm text-muted-foreground">Keine Ereignisse gefunden.</p>;
  }

  const events = [...content.events].sort((a, b) => {
    if (!a.date && !b.date) return 0;
    if (!a.date) return 1;
    if (!b.date) return -1;
    return a.date.localeCompare(b.date);
  });

  return (
    <ol className="mx-auto flex max-w-2xl flex-col gap-5 border-l border-border pl-5">
      {events.map((event, index) => (
        <li key={index} className="relative">
          <span className="absolute -left-[25px] top-1 h-3 w-3 rounded-full border-2 border-background bg-primary" />
          <p className="text-xs font-semibold text-primary">{event.date_label}</p>
          <p className="mt-1 text-sm text-foreground">{event.description}</p>
          <p className="mt-1.5 text-xs italic text-muted-foreground">&ldquo;{event.quote}&rdquo;</p>
        </li>
      ))}
    </ol>
  );
}

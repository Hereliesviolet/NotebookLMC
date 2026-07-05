import type { StudioInfographicContent } from "@/lib/types";

export function StudioInfographicView({ content }: { content: StudioInfographicContent }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg bg-primary px-6 py-6 text-primary-foreground">
        <h1 className="text-2xl font-bold">{content.headline}</h1>
        <p className="mt-1.5 text-sm text-primary-foreground/85">{content.subheadline}</p>
      </div>

      {content.stats.length > 0 && (
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${content.stats.length}, minmax(0, 1fr))` }}>
          {content.stats.map((stat, index) => (
            <div key={index} className="rounded-md border border-border bg-primary/10 px-3 py-3 text-center">
              <div className="text-xl font-bold text-primary">{stat.value}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {content.sections.map((section, index) => (
          <div key={index} className="rounded-md border border-border p-4">
            <div className="mb-1.5 flex items-center gap-2">
              <span className="flex h-[18px] w-[18px] flex-none items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                {index + 1}
              </span>
              <h3 className="text-sm font-bold text-primary">{section.title}</h3>
            </div>
            <p className="text-sm text-foreground">{section.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

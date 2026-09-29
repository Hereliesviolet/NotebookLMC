import { AlertTriangle, CheckCircle2, HelpCircle, ListChecks, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownContent } from "@/components/ui/markdown-content";
import type { StudioBriefingContent } from "@/lib/types";

const SECTIONS: Array<{
  key: "key_points" | "risks" | "recommended_actions" | "open_questions";
  title: string;
  icon: LucideIcon;
  accent: string;
}> = [
  { key: "key_points", title: "Kernpunkte", icon: ListChecks, accent: "text-primary" },
  { key: "risks", title: "Risiken", icon: AlertTriangle, accent: "text-red-600" },
  {
    key: "recommended_actions",
    title: "Empfohlene Maßnahmen",
    icon: CheckCircle2,
    accent: "text-emerald-600",
  },
  { key: "open_questions", title: "Offene Fragen", icon: HelpCircle, accent: "text-amber-600" },
];

export function StudioBriefingView({ content }: { content: StudioBriefingContent }) {
  return (
    <div className="flex flex-col gap-6">
      <MarkdownContent content={content.summary} />
      <div className="grid gap-4 sm:grid-cols-2">
        {SECTIONS.map(({ key, title, icon: Icon, accent }) => {
          const items = content[key];
          if (!items || items.length === 0) return null;
          return (
            <div key={key} className="rounded-md border border-border p-4">
              <div className={cn("mb-3 flex items-center gap-1.5 text-xs font-semibold", accent)}>
                <Icon className="h-3.5 w-3.5" />
                {title}
              </div>
              <ul className="flex flex-col gap-2 text-sm text-foreground">
                {items.map((item, index) => (
                  <li key={index} className="flex gap-2">
                    <span className="text-muted-foreground">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { FileText, HelpCircle, GanttChartSquare, ClipboardList, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StudioFullscreenOverlay } from "@/components/studio/StudioFullscreenOverlay";
import { getStudioArtifact } from "@/lib/api-client";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { StudioArtifact, StudioArtifactType } from "@/lib/types";

interface StudioFeature {
  type: StudioArtifactType;
  icon: LucideIcon;
  title: string;
  description: string;
}

const STUDIO_FEATURES: StudioFeature[] = [
  { type: "summary", icon: FileText, title: "Zusammenfassung", description: "Notebook- und Quellenzusammenfassungen" },
  { type: "faq", icon: HelpCircle, title: "FAQ", description: "Häufige Fragen aus den Quellen ableiten" },
  { type: "timeline", icon: GanttChartSquare, title: "Timeline", description: "Chronologie über mehrere Quellen" },
  { type: "briefing", icon: ClipboardList, title: "Briefing", description: "Kompaktes Entscheidungs-Briefing" },
];

type ArtifactStatus = StudioArtifact<unknown> | null | undefined;

export function StudioPanel({ notebookId }: { notebookId: string }) {
  const [activeType, setActiveType] = useState<StudioArtifactType | null>(null);
  const [statuses, setStatuses] = useState<Partial<Record<StudioArtifactType, ArtifactStatus>>>({});

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled(STUDIO_FEATURES.map((feature) => getStudioArtifact<unknown>(notebookId, feature.type))).then(
      (results) => {
        if (cancelled) return;
        setStatuses(
          Object.fromEntries(
            STUDIO_FEATURES.map((feature, index) => {
              const result = results[index];
              return [feature.type, result.status === "fulfilled" ? result.value : null];
            })
          )
        );
      }
    );
    return () => {
      cancelled = true;
    };
  }, [notebookId]);

  const active = STUDIO_FEATURES.find((feature) => feature.type === activeType);

  function statusLabel(status: ArtifactStatus) {
    if (status === undefined) return "Lädt…";
    if (status === null) return "Noch nicht erstellt";
    return `Aktualisiert ${formatRelativeTime(status.updated_at)}`;
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <h2 className="text-sm font-semibold">Studio</h2>
      <p className="text-xs text-muted-foreground">
        Zusammenfassungen, FAQ, Timeline und Briefings aus deinen Quellen generieren.
      </p>

      <div className="flex flex-col gap-2">
        {STUDIO_FEATURES.map(({ type, icon: Icon, title, description }) => {
          const status = statuses[type];
          return (
            <Card
              key={type}
              onClick={() => setActiveType(type)}
              className="flex cursor-pointer flex-row items-center gap-3 p-3 transition-shadow hover:shadow-md"
            >
              <Icon className="h-5 w-5 shrink-0 text-primary" />
              <div className="flex flex-col gap-0.5">
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="text-xs leading-snug text-muted-foreground">{description}</p>
                <p
                  className={cn(
                    "mt-0.5 text-[11px] font-medium",
                    status ? "text-emerald-600" : "text-muted-foreground"
                  )}
                >
                  {statusLabel(status)}
                </p>
              </div>
            </Card>
          );
        })}
      </div>

      {active && (
        <StudioFullscreenOverlay
          key={active.type}
          notebookId={notebookId}
          type={active.type}
          title={active.title}
          onClose={() => setActiveType(null)}
          onArtifactChange={(artifact) => setStatuses((prev) => ({ ...prev, [active.type]: artifact }))}
        />
      )}
    </div>
  );
}

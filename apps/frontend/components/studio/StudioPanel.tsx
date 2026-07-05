import { FileText, HelpCircle, GanttChartSquare, ClipboardList } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const STUDIO_FEATURES = [
  { icon: FileText, title: "Zusammenfassung", description: "Notebook- und Quellenzusammenfassungen" },
  { icon: HelpCircle, title: "FAQ", description: "Häufige Fragen aus den Quellen ableiten" },
  { icon: GanttChartSquare, title: "Timeline", description: "Chronologie über mehrere Quellen" },
  { icon: ClipboardList, title: "Briefing", description: "Kompaktes Entscheidungs-Briefing" },
] as const;

/**
 * MVP2 feature per architecture doc §19 - the backend endpoints exist as
 * placeholders (app.studio.router) but aren't functionally implemented yet.
 * This panel documents the planned Studio surface without making calls
 * that would currently just 501.
 */
export function StudioPanel() {
  return (
    <div className="flex flex-col gap-3 p-4">
      <h2 className="text-sm font-semibold">Studio</h2>
      <p className="text-xs text-muted-foreground">
        Zusammenfassungen, FAQ, Timeline und Briefings folgen in MVP2.
      </p>
      {STUDIO_FEATURES.map(({ icon: Icon, title, description }) => (
        <Card key={title} className="opacity-70">
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Icon className="h-4 w-4 text-muted-foreground" />
            <CardTitle>{title}</CardTitle>
            <Badge variant="muted" className="ml-auto">
              Bald verfügbar
            </Badge>
          </CardHeader>
          <CardContent className="pt-0 text-xs text-muted-foreground">{description}</CardContent>
        </Card>
      ))}
    </div>
  );
}

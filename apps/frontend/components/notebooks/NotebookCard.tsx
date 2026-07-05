import Link from "next/link";
import { FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";
import type { Notebook } from "@/lib/types";

export function NotebookCard({ notebook }: { notebook: Notebook }) {
  return (
    <Link href={`/notebooks/${notebook.id}`}>
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardHeader>
          <CardTitle className="line-clamp-1">{notebook.title}</CardTitle>
          <CardDescription className="line-clamp-2">
            {notebook.description || "Keine Beschreibung"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <FileText className="h-3.5 w-3.5" />
            {notebook.source_count} Quelle{notebook.source_count === 1 ? "" : "n"}
          </span>
          <span>{formatDate(notebook.updated_at)}</span>
        </CardContent>
      </Card>
    </Link>
  );
}

import { FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { Citation } from "@/lib/types";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const pageLabel =
    citation.page_start != null
      ? citation.page_start === citation.page_end
        ? `Seite ${citation.page_start}`
        : `Seite ${citation.page_start}–${citation.page_end}`
      : null;

  return (
    <Card className="bg-muted/40">
      <CardContent className="flex flex-col gap-1 p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <FileText className="h-3.5 w-3.5" />
          Quelle {index + 1} · {citation.document_name}
          {pageLabel ? ` · ${pageLabel}` : ""}
        </div>
        <p className="text-sm italic text-foreground/90">&ldquo;{citation.quote}&rdquo;</p>
      </CardContent>
    </Card>
  );
}

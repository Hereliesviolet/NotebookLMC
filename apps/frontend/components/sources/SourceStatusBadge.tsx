import { Badge } from "@/components/ui/badge";
import type { SourceStatus } from "@/lib/types";

const LABELS: Record<SourceStatus, string> = {
  uploaded: "Hochgeladen",
  processing: "Wird verarbeitet",
  indexed: "Indexiert",
  failed: "Fehlgeschlagen",
  no_content: "Kein Text erkannt",
  deleted: "Gelöscht",
};

const VARIANTS: Record<SourceStatus, "default" | "success" | "warning" | "destructive" | "muted"> =
  {
    uploaded: "muted",
    processing: "warning",
    indexed: "success",
    failed: "destructive",
    no_content: "destructive",
    deleted: "muted",
  };

export function SourceStatusBadge({ status }: { status: SourceStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>;
}

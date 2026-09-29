"use client";

import { File, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SourceStatusBadge } from "@/components/sources/SourceStatusBadge";
import type { Source } from "@/lib/types";

interface SourceCardProps {
  source: Source;
  onDelete: (id: string) => void;
}

export function SourceCard({ source, onDelete }: SourceCardProps) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2">
      <div className="flex min-w-0 items-center gap-2">
        <File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium" title={source.original_filename}>
            {source.original_filename}
          </p>
          {source.error_message && (
            <p className="truncate text-xs text-red-600" title={source.error_message}>
              {source.error_message}
            </p>
          )}
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        <SourceStatusBadge status={source.status} />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(source.id)}
          aria-label="Quelle löschen"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

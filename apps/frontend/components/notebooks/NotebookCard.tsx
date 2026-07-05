"use client";

import { useState, type MouseEvent } from "react";
import Link from "next/link";
import { FileText, Loader2, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { deleteNotebook } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import type { Notebook } from "@/lib/types";

interface NotebookCardProps {
  notebook: Notebook;
  onDelete: (id: string) => void;
}

export function NotebookCard({ notebook, onDelete }: NotebookCardProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openConfirm(event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    setError(null);
    setConfirmOpen(true);
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteNotebook(notebook.id);
      setConfirmOpen(false);
      onDelete(notebook.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notebook konnte nicht gelöscht werden.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="group relative h-full">
        <Link href={`/notebooks/${notebook.id}`} className="block h-full">
          <Card className="h-full transition-shadow hover:shadow-md">
            <CardHeader>
              <CardTitle className="line-clamp-1 pr-6">{notebook.title}</CardTitle>
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
        <Button
          variant="ghost"
          size="icon"
          onClick={openConfirm}
          aria-label="Notebook löschen"
          className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <Dialog open={confirmOpen} onClose={() => !deleting && setConfirmOpen(false)}>
        <div className="flex flex-col gap-4">
          <h2 className="text-sm font-semibold">Notebook löschen</h2>
          <p className="text-sm text-muted-foreground">
            Möchtest du <span className="font-medium text-foreground">„{notebook.title}“</span> wirklich
            unwiderruflich löschen? Alle Quellen, Chats und Notizen gehen dabei verloren.
          </p>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setConfirmOpen(false)} disabled={deleting}>
              Abbrechen
            </Button>
            <Button type="button" variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Wird gelöscht…
                </>
              ) : (
                "Löschen"
              )}
            </Button>
          </div>
        </div>
      </Dialog>
    </>
  );
}

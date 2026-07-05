"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NotebookCard } from "@/components/notebooks/NotebookCard";
import { CreateNotebookDialog } from "@/components/notebooks/CreateNotebookDialog";
import { listNotebooks } from "@/lib/api-client";
import type { Notebook } from "@/lib/types";

export default function NotebooksPage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    listNotebooks()
      .then(setNotebooks)
      .catch((err) => setError(err instanceof Error ? err.message : "Fehler beim Laden"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Notebooks</h1>
          <p className="text-sm text-muted-foreground">Deine quellenbasierten Research-Workspaces.</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" />
          Neues Notebook
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Lädt…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && notebooks.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
          Noch keine Notebooks. Erstelle dein erstes Notebook, um Quellen hochzuladen.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {notebooks.map((notebook) => (
          <NotebookCard key={notebook.id} notebook={notebook} />
        ))}
      </div>

      <CreateNotebookDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(notebook) => setNotebooks((prev) => [notebook, ...prev])}
      />
    </div>
  );
}

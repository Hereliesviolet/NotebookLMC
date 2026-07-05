"use client";

import { FormEvent, useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createNotebook } from "@/lib/api-client";
import type { Notebook } from "@/lib/types";

interface CreateNotebookDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (notebook: Notebook) => void;
}

export function CreateNotebookDialog({ open, onClose, onCreated }: CreateNotebookDialogProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const notebook = await createNotebook(title.trim(), description.trim() || undefined);
      onCreated(notebook);
      setTitle("");
      setDescription("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notebook konnte nicht erstellt werden.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold">Neues Notebook</h2>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">Titel</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z. B. Gutachten Schadensfall" autoFocus />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">Beschreibung (optional)</label>
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Abbrechen
          </Button>
          <Button type="submit" disabled={submitting || !title.trim()}>
            {submitting ? "Wird erstellt…" : "Erstellen"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

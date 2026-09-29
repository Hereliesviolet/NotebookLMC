"use client";

import { useEffect, useState } from "react";
import { Plus, StickyNote } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createNote, listNotes } from "@/lib/api-client";
import type { Note } from "@/lib/types";

export function NotesPanel({ notebookId }: { notebookId: string }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  useEffect(() => {
    listNotes(notebookId)
      .then(setNotes)
      .catch(() => undefined);
  }, [notebookId]);

  async function handleCreate() {
    if (!title.trim() || !content.trim()) return;
    const note = await createNote(notebookId, title.trim(), content.trim());
    setNotes((prev) => [note, ...prev]);
    setTitle("");
    setContent("");
    setCreating(false);
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold">
          <StickyNote className="h-4 w-4" />
          Notizen
        </h2>
        <Button variant="ghost" size="icon" onClick={() => setCreating((v) => !v)}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {creating && (
        <Card>
          <CardContent className="flex flex-col gap-2 p-3">
            <Input placeholder="Titel" value={title} onChange={(e) => setTitle(e.target.value)} />
            <Textarea
              placeholder="Inhalt"
              rows={3}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <Button size="sm" onClick={handleCreate}>
              Speichern
            </Button>
          </CardContent>
        </Card>
      )}

      {notes.map((note) => (
        <Card key={note.id}>
          <CardHeader>
            <CardTitle>{note.title}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-sm text-muted-foreground whitespace-pre-wrap">
            {note.content}
          </CardContent>
        </Card>
      ))}

      {notes.length === 0 && !creating && (
        <p className="text-xs text-muted-foreground">
          Noch keine Notizen. Übernimm Antworten aus dem Chat oder lege eine neue Notiz an.
        </p>
      )}
    </div>
  );
}

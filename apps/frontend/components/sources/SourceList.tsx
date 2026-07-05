"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { UploadDropzone } from "@/components/sources/UploadDropzone";
import { SourceCard } from "@/components/sources/SourceCard";
import { deleteSource, listSources, uploadSource } from "@/lib/api-client";
import type { Source } from "@/lib/types";

const POLL_INTERVAL_MS = 4000;

export function SourceList({ notebookId }: { notebookId: string }) {
  const [sources, setSources] = useState<Source[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(() => {
    listSources(notebookId).then(setSources).catch(() => undefined);
  }, [notebookId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const hasPending = sources.some((s) => s.status === "uploaded" || s.status === "processing");
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(refresh, POLL_INTERVAL_MS);
    }
    if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [sources, refresh]);

  async function handleFiles(files: File[]) {
    setUploading(true);
    setError(null);
    try {
      for (const file of files) {
        const source = await uploadSource(notebookId, file);
        setSources((prev) => [source, ...prev]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload fehlgeschlagen");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    setSources((prev) => prev.filter((s) => s.id !== id));
    try {
      await deleteSource(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Löschen fehlgeschlagen");
      refresh();
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <UploadDropzone onFiles={handleFiles} disabled={uploading} />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex flex-col gap-2">
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} onDelete={handleDelete} />
        ))}
        {sources.length === 0 && (
          <p className="px-1 text-xs text-muted-foreground">Noch keine Quellen hochgeladen.</p>
        )}
      </div>
    </div>
  );
}

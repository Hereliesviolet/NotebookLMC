"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchStudioInfographicImage } from "@/lib/api-client";
import type { StudioInfographicContent } from "@/lib/types";

interface StudioInfographicViewProps {
  notebookId: string;
  content: StudioInfographicContent;
  refreshKey: number;
}

export function StudioInfographicView({ notebookId, content, refreshKey }: StudioInfographicViewProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);
    fetchStudioInfographicImage(notebookId, refreshKey)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setImageUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Grafik konnte nicht geladen werden.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [notebookId, refreshKey]);

  function handleDownload() {
    if (!imageUrl) return;
    const link = document.createElement("a");
    link.href = imageUrl;
    link.download = "infografik.png";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-4">
      <div className="text-center">
        <p className="text-lg font-semibold text-foreground">{content.headline}</p>
        <p className="text-sm text-muted-foreground">{content.subheadline}</p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Grafik wird geladen…</p>}
      {!loading && error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && imageUrl && (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl} alt={content.headline} className="max-w-full rounded-md border border-border shadow-sm" />
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="h-3.5 w-3.5" />
            PNG herunterladen
          </Button>
        </>
      )}
    </div>
  );
}

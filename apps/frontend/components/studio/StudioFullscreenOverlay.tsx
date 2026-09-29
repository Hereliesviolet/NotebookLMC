"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, Download, Loader2, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { StudioFaqView } from "@/components/studio/StudioFaqView";
import { StudioTimelineView } from "@/components/studio/StudioTimelineView";
import { StudioBriefingView } from "@/components/studio/StudioBriefingView";
import { StudioQuizView } from "@/components/studio/StudioQuizView";
import { StudioMindmapView } from "@/components/studio/StudioMindmapView";
import { StudioInfographicView } from "@/components/studio/StudioInfographicView";
import { exportStudioArtifact, generateStudioArtifact, getStudioArtifact } from "@/lib/api-client";
import { useElapsedSeconds } from "@/lib/use-elapsed-seconds";
import { cn, formatDate } from "@/lib/utils";
import type {
  StudioArtifact,
  StudioArtifactType,
  StudioBriefingContent,
  StudioFaqContent,
  StudioInfographicContent,
  StudioMindmapContent,
  StudioQuizContent,
  StudioSummaryContent,
  StudioTimelineContent,
} from "@/lib/types";

type AnyStudioContent =
  | StudioSummaryContent
  | StudioFaqContent
  | StudioTimelineContent
  | StudioBriefingContent
  | StudioQuizContent
  | StudioMindmapContent
  | StudioInfographicContent;

interface StudioFullscreenOverlayProps {
  notebookId: string;
  type: StudioArtifactType;
  title: string;
  onClose: () => void;
  onArtifactChange?: (artifact: StudioArtifact<AnyStudioContent>) => void;
}

export function StudioFullscreenOverlay({
  notebookId,
  type,
  title,
  onClose,
  onArtifactChange,
}: StudioFullscreenOverlayProps) {
  const [visible, setVisible] = useState(false);
  const [artifact, setArtifact] = useState<StudioArtifact<AnyStudioContent> | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [exportFormat, setExportFormat] = useState<"docx" | "pdf" | "png" | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renderRefreshKey, setRenderRefreshKey] = useState(() => Date.now());
  const generatingElapsedSeconds = useElapsedSeconds(generating);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true));
    document.body.style.overflow = "hidden";
    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = "";
    };
  }, []);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(onClose, 180);
  }, [onClose]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") handleClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleClose]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getStudioArtifact<AnyStudioContent>(notebookId, type)
      .then((result) => {
        if (!cancelled) setArtifact(result);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Inhalt konnte nicht geladen werden.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [notebookId, type]);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const result = await generateStudioArtifact<AnyStudioContent>(notebookId, type);
      setArtifact(result);
      setRenderRefreshKey(Date.now());
      onArtifactChange?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inhalt konnte nicht generiert werden.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleExport(format: "docx" | "pdf" | "png") {
    setExportMenuOpen(false);
    setExportFormat(format);
    setError(null);
    try {
      await exportStudioArtifact(notebookId, type, format);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export fehlgeschlagen.");
    } finally {
      setExportFormat(null);
    }
  }

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex flex-col bg-background transition-opacity duration-200",
        visible ? "opacity-100" : "opacity-0"
      )}
    >
      <div
        className={cn(
          "flex h-full flex-col transition-transform duration-200",
          visible ? "translate-y-0" : "translate-y-3"
        )}
      >
        <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
            {artifact && (
              <p className="text-xs text-muted-foreground">
                Zuletzt aktualisiert: {formatDate(artifact.updated_at)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {artifact && type !== "quiz" && (
              <div className="relative">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setExportMenuOpen((value) => !value)}
                >
                  <Download className="h-3.5 w-3.5" />
                  Exportieren
                  <ChevronDown
                    className={cn(
                      "h-3.5 w-3.5 transition-transform",
                      exportMenuOpen && "rotate-180"
                    )}
                  />
                </Button>
                {exportMenuOpen && (
                  <div className="absolute right-0 top-full z-10 mt-1 w-40 overflow-hidden rounded-md border border-border bg-card shadow-lg">
                    {(type === "infographic"
                      ? (["pdf"] as const)
                      : type === "mindmap"
                        ? (["png"] as const)
                        : (["docx", "pdf"] as const)
                    ).map((format) => (
                      <button
                        key={format}
                        onClick={() => handleExport(format)}
                        disabled={exportFormat !== null}
                        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-muted disabled:opacity-50"
                      >
                        Als {format === "docx" ? "Word" : format === "pdf" ? "PDF" : "PNG"}
                        {exportFormat === format && (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {artifact && (
              <Button variant="outline" size="sm" onClick={handleGenerate} disabled={generating}>
                {generating ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Wird generiert… ({generatingElapsedSeconds}s)
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-3.5 w-3.5" />
                    Neu generieren
                  </>
                )}
              </Button>
            )}
            <button
              onClick={handleClose}
              aria-label="Schließen"
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        <div
          className={cn(
            "flex-1 overflow-y-auto",
            type === "mindmap" ? "flex flex-col p-6" : "px-6 py-8"
          )}
        >
          <div className={cn(type === "mindmap" ? "flex flex-1 flex-col" : "mx-auto max-w-4xl")}>
            {loading && <p className="text-sm text-muted-foreground">Lädt…</p>}
            {!loading && error && <p className="text-sm text-red-600">{error}</p>}

            {!loading && !artifact && !error && (
              <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border p-12 text-center">
                <p className="text-sm text-muted-foreground">Noch nicht generiert.</p>
                <Button onClick={handleGenerate} disabled={generating}>
                  {generating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Wird generiert… ({generatingElapsedSeconds}s)
                    </>
                  ) : (
                    "Generieren"
                  )}
                </Button>
              </div>
            )}

            {!loading && artifact && (
              <StudioArtifactContent
                type={type}
                content={artifact.content}
                renderRefreshKey={renderRefreshKey}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StudioArtifactContent({
  type,
  content,
  renderRefreshKey,
}: {
  type: StudioArtifactType;
  content: AnyStudioContent;
  renderRefreshKey: number;
}) {
  switch (type) {
    case "summary":
      return <MarkdownContent content={(content as StudioSummaryContent).summary_markdown} />;
    case "faq":
      return <StudioFaqView content={content as StudioFaqContent} />;
    case "timeline":
      return <StudioTimelineView content={content as StudioTimelineContent} />;
    case "briefing":
      return <StudioBriefingView content={content as StudioBriefingContent} />;
    case "quiz":
      return <StudioQuizView key={renderRefreshKey} content={content as StudioQuizContent} />;
    case "mindmap":
      return <StudioMindmapView key={renderRefreshKey} content={content as StudioMindmapContent} />;
    case "infographic":
      return <StudioInfographicView content={content as StudioInfographicContent} />;
    default:
      return null;
  }
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { SourceList } from "@/components/sources/SourceList";
import { NotesPanel } from "@/components/notes/NotesPanel";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { StudioPanel } from "@/components/studio/StudioPanel";
import { getNotebook } from "@/lib/api-client";
import type { Notebook } from "@/lib/types";

type LeftTab = "sources" | "notes";

export default function NotebookDetailPage({ params }: { params: { id: string } }) {
  const notebookId = params.id;
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [leftTab, setLeftTab] = useState<LeftTab>("sources");

  useEffect(() => {
    getNotebook(notebookId).then(setNotebook).catch(() => undefined);
  }, [notebookId]);

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center gap-3 border-b border-border px-6 py-3">
        <Link href="/" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="text-sm font-semibold">{notebook?.title ?? "Notebook"}</h1>
      </header>

      <div className="grid flex-1 grid-cols-[280px_1fr_280px] overflow-hidden">
        <section className="flex flex-col overflow-y-auto border-r border-border">
          <div className="flex border-b border-border text-sm">
            <button
              className={`flex-1 px-3 py-2 ${leftTab === "sources" ? "border-b-2 border-primary font-medium" : "text-muted-foreground"}`}
              onClick={() => setLeftTab("sources")}
            >
              Quellen
            </button>
            <button
              className={`flex-1 px-3 py-2 ${leftTab === "notes" ? "border-b-2 border-primary font-medium" : "text-muted-foreground"}`}
              onClick={() => setLeftTab("notes")}
            >
              Notizen
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {leftTab === "sources" ? (
              <div className="p-4">
                <SourceList notebookId={notebookId} />
              </div>
            ) : (
              <NotesPanel notebookId={notebookId} />
            )}
          </div>
        </section>

        <section className="flex flex-col overflow-hidden">
          <ChatPanel notebookId={notebookId} />
        </section>

        <section className="overflow-y-auto border-l border-border">
          <StudioPanel />
        </section>
      </div>
    </div>
  );
}

"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { SourceList } from "@/components/sources/SourceList";
import { NotesPanel } from "@/components/notes/NotesPanel";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { StudioPanel } from "@/components/studio/StudioPanel";
import { getNotebook } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Notebook } from "@/lib/types";

type LeftTab = "sources" | "notes";
type MobileTab = "sources" | "chat" | "studio";

// Next.js 15: `params` ist in Page-Komponenten jetzt ein Promise (auch bei
// Client Components) und muss ueber React's use() aufgeloest werden.
export default function NotebookDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const notebookId = use(params).id;
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [leftTab, setLeftTab] = useState<LeftTab>("sources");
  const [mobileTab, setMobileTab] = useState<MobileTab>("chat");

  useEffect(() => {
    getNotebook(notebookId).then(setNotebook).catch(() => undefined);
  }, [notebookId]);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-border px-6 py-3">
        <Link href="/" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="text-sm font-semibold">{notebook?.title ?? "Notebook"}</h1>
      </header>

      <div className="flex border-b border-border text-sm lg:hidden">
        <button
          className={`flex-1 px-3 py-2 ${mobileTab === "sources" ? "border-b-2 border-primary font-medium" : "text-muted-foreground"}`}
          onClick={() => setMobileTab("sources")}
        >
          Quellen
        </button>
        <button
          className={`flex-1 px-3 py-2 ${mobileTab === "chat" ? "border-b-2 border-primary font-medium" : "text-muted-foreground"}`}
          onClick={() => setMobileTab("chat")}
        >
          Chat
        </button>
        <button
          className={`flex-1 px-3 py-2 ${mobileTab === "studio" ? "border-b-2 border-primary font-medium" : "text-muted-foreground"}`}
          onClick={() => setMobileTab("studio")}
        >
          Studio
        </button>
      </div>

      <div className="grid flex-1 overflow-hidden lg:grid-cols-[280px_1fr_280px]">
        <section
          className={cn(
            "flex-col overflow-y-auto border-r border-border lg:flex",
            mobileTab === "sources" ? "flex" : "hidden"
          )}
        >
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

        <section
          className={cn("flex-col overflow-hidden lg:flex", mobileTab === "chat" ? "flex" : "hidden")}
        >
          <ChatPanel notebookId={notebookId} />
        </section>

        <section
          className={cn("overflow-y-auto border-l border-border lg:block", mobileTab === "studio" ? "block" : "hidden")}
        >
          <StudioPanel notebookId={notebookId} />
        </section>
      </div>
    </div>
  );
}

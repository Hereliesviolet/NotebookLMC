"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut, NotebookText } from "lucide-react";
import { logout } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

export function Sidebar() {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  }

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-border bg-muted/40 p-4">
      <Link href="/" className="mb-6 flex items-center gap-2 px-1 text-sm font-semibold">
        <NotebookText className="h-5 w-5 text-primary" />
        NotebookLM Clone
      </Link>
      <nav className="flex flex-col gap-1 text-sm">
        <Link href="/" className="rounded-md px-3 py-2 hover:bg-muted">
          Notebooks
        </Link>
      </nav>
      <div className="mt-auto flex flex-col gap-2">
        <Button variant="ghost" size="sm" className="justify-start gap-2" onClick={handleLogout} disabled={loggingOut}>
          <LogOut className="h-4 w-4" />
          {loggingOut ? "Wird abgemeldet…" : "Abmelden"}
        </Button>
        <div className="px-3 py-2 text-xs text-muted-foreground">Self-hosted · Langdock AI Gateway</div>
      </div>
    </aside>
  );
}

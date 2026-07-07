"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut, NotebookText } from "lucide-react";
import { logout } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={onClose} />
          <SidebarContent
            className="relative flex h-full w-60 flex-col border-r border-border bg-background p-4 shadow-lg"
            onNavigate={onClose}
          />
        </div>
      )}
      <SidebarContent className="hidden h-screen w-60 flex-col border-r border-border bg-background p-4 md:flex" />
    </>
  );
}

function SidebarContent({ className, onNavigate }: { className: string; onNavigate?: () => void }) {
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
    <aside className={className}>
      <Link href="/" className="mb-6 flex items-center gap-2 px-1 text-sm font-semibold" onClick={onNavigate}>
        <NotebookText className="h-5 w-5 text-primary" />
        NotebookLM Clone
      </Link>
      <nav className="flex flex-col gap-1 text-sm">
        <Link href="/" className="rounded-md px-3 py-2 hover:bg-muted" onClick={onNavigate}>
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

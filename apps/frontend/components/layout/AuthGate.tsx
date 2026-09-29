"use client";

import { ReactNode, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Menu, NotebookText } from "lucide-react";
import { getMe } from "@/lib/api-client";
import { Sidebar } from "@/components/layout/Sidebar";

const PUBLIC_ROUTES = new Set(["/login", "/register"]);

/**
 * Gatekeeper for the real email/password + session-cookie auth (see
 * docs/security.md). On protected routes it checks session validity via
 * GET /api/auth/me and redirects to /login on 401. Login/register pages
 * skip this check entirely (no session exists yet) and render without the
 * app chrome (Sidebar).
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublicRoute = PUBLIC_ROUTES.has(pathname);
  const [status, setStatus] = useState<"checking" | "authenticated">(
    isPublicRoute ? "authenticated" : "checking"
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (isPublicRoute) return;
    let cancelled = false;
    getMe()
      .then(() => {
        if (!cancelled) setStatus("authenticated");
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [isPublicRoute, pathname, router]);

  if (isPublicRoute) {
    return <>{children}</>;
  }

  if (status === "checking") {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Lädt…
      </div>
    );
  }

  return (
    <div className="flex">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border px-4 py-3 md:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Menü öffnen"
            className="rounded-md p-1.5 text-foreground hover:bg-muted"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="flex items-center gap-2 text-sm font-semibold">
            <NotebookText className="h-5 w-5 text-primary" />
            NotebookLM Clone
          </span>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

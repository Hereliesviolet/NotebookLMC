"use client";

import { ReactNode, useEffect, useState } from "react";
import { getToken, login } from "@/lib/api-client";

/**
 * Dev/demo auth bootstrap (architecture doc §21.1): silently logs in as the
 * demo user on first load so the MVP has zero login friction. Swap this for
 * a real login screen once SSO (§21.2) lands - everything else in the app
 * only depends on a token being present in localStorage.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    async function ensureAuth() {
      if (!getToken()) {
        await login();
      }
      setReady(true);
    }
    ensureAuth().catch((err) => {
      console.error("Dev auto-login failed", err);
      setReady(true);
    });
  }, []);

  if (!ready) {
    return <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">Lädt…</div>;
  }

  return <>{children}</>;
}

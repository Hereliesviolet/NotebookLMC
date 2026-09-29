"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { NotebookText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { login } from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.replace("/");
    } catch {
      setError(
        "E-Mail oder Passwort ist falsch, oder es gab zu viele Versuche. Bitte erneut versuchen."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <NotebookText className="mb-2 h-8 w-8 text-primary" />
          <CardTitle>Anmelden</CardTitle>
          <CardDescription>Melde dich mit deiner E-Mail und deinem Passwort an.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">E-Mail</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">Passwort</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <Button
              type="submit"
              disabled={submitting || !email.trim() || !password}
              className="w-full"
            >
              {submitting ? "Wird angemeldet…" : "Anmelden"}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              Noch kein Konto?{" "}
              <Link href="/register" className="font-medium text-primary hover:underline">
                Registrieren
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

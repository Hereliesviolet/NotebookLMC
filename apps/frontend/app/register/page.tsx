"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { NotebookText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { register } from "@/lib/api-client";

const MIN_PASSWORD_LENGTH = 10;

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await register(email.trim(), password, name.trim());
      setSuccess(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (message.includes("409")) {
        setError("Für diese E-Mail existiert bereits ein Konto.");
      } else if (message.includes("422")) {
        setError(`Das Passwort muss mindestens ${MIN_PASSWORD_LENGTH} Zeichen haben.`);
      } else {
        setError("Registrierung fehlgeschlagen. Bitte erneut versuchen.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
        <Card className="w-full max-w-sm">
          <CardHeader className="items-center text-center">
            <NotebookText className="mb-2 h-8 w-8 text-primary" />
            <CardTitle>Konto erstellt</CardTitle>
            <CardDescription>Du kannst dich jetzt mit deinen Zugangsdaten anmelden.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" onClick={() => router.replace("/login")}>
              Zum Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <NotebookText className="mb-2 h-8 w-8 text-primary" />
          <CardTitle>Konto erstellen</CardTitle>
          <CardDescription>Registriere dich mit deiner E-Mail-Adresse.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus autoComplete="name" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">E-Mail</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
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
                minLength={MIN_PASSWORD_LENGTH}
                autoComplete="new-password"
              />
              <p className="text-xs text-muted-foreground">Mindestens {MIN_PASSWORD_LENGTH} Zeichen.</p>
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <Button
              type="submit"
              disabled={submitting || !name.trim() || !email.trim() || password.length < MIN_PASSWORD_LENGTH}
              className="w-full"
            >
              {submitting ? "Wird erstellt…" : "Registrieren"}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              Bereits registriert?{" "}
              <Link href="/login" className="font-medium text-primary hover:underline">
                Anmelden
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

import Link from "next/link";
import { NotebookText } from "lucide-react";

export function Sidebar() {
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
      <div className="mt-auto px-3 py-2 text-xs text-muted-foreground">Self-hosted · Langdock AI Gateway</div>
    </aside>
  );
}

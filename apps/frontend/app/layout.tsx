import type { Metadata } from "next";
import "./globals.css";
import { AuthGate } from "@/components/layout/AuthGate";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "NotebookLM Clone",
  description: "Self-hosted, source-grounded research workspace powered by Langdock.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="font-sans antialiased">
        <AuthGate>
          <div className="flex">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">{children}</main>
          </div>
        </AuthGate>
      </body>
    </html>
  );
}

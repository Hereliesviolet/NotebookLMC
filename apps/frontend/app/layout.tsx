import type { Metadata } from "next";
import "./globals.css";
import { AuthGate } from "@/components/layout/AuthGate";

export const metadata: Metadata = {
  title: "NotebookLM Clone",
  description: "Self-hosted, source-grounded research workspace powered by Langdock.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="font-sans antialiased">
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}

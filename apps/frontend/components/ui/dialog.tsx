"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}

export function Dialog({ open, onClose, children, className }: DialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="absolute inset-0" onClick={onClose} />
      <div className={cn("relative w-full max-w-md rounded-lg border border-border bg-card p-5 shadow-lg", className)}>
        {children}
      </div>
    </div>
  );
}

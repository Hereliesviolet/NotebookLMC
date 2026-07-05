"use client";

import { DragEvent, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadDropzoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.txt,.md,.markdown,.html,.csv,.xlsx";

export function UploadDropzone({ onFiles, disabled }: UploadDropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    const files = Array.from(event.dataTransfer.files);
    if (files.length) onFiles(files);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border p-6 text-center transition-colors",
        dragging && "border-primary bg-primary/5",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <UploadCloud className="h-6 w-6 text-muted-foreground" />
      <p className="text-sm font-medium">Dateien hier ablegen oder klicken</p>
      <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, Markdown, HTML, CSV, XLSX</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_EXTENSIONS}
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StudioMindmapChild, StudioMindmapContent, StudioMindmapLeaf } from "@/lib/types";

export function StudioMindmapView({ content }: { content: StudioMindmapContent }) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-2">
      <div className="inline-block self-start rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground">
        {content.root.label}
      </div>
      <div className="flex flex-col gap-1 border-l border-border pl-4">
        {content.root.children.map((child, index) => (
          <MindmapBranch key={index} child={child} />
        ))}
      </div>
    </div>
  );
}

function MindmapBranch({ child }: { child: StudioMindmapChild }) {
  const [open, setOpen] = useState(true);
  const hasChildren = child.children.length > 0;

  return (
    <div className="flex flex-col gap-1 py-1">
      <button
        type="button"
        onClick={() => hasChildren && setOpen((value) => !value)}
        disabled={!hasChildren}
        className="flex items-center gap-1.5 text-left text-sm font-medium text-foreground disabled:cursor-default"
      >
        {hasChildren && (
          <ChevronDown className={cn("h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
        )}
        {!hasChildren && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground" />}
        <span>{child.label}</span>
      </button>
      {hasChildren && open && (
        <div className="ml-2 flex flex-col gap-1 border-l border-border pl-4">
          {child.children.map((leaf, index) => (
            <MindmapLeaf key={index} leaf={leaf} />
          ))}
        </div>
      )}
    </div>
  );
}

function MindmapLeaf({ leaf }: { leaf: StudioMindmapLeaf }) {
  return (
    <div className="flex items-center gap-1.5 py-0.5 text-sm text-muted-foreground">
      <span className="h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />
      <span>{leaf.label}</span>
    </div>
  );
}

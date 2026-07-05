import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

const MARKDOWN_CLASSNAMES = cn(
  "prose prose-sm max-w-none text-foreground",
  "prose-headings:font-semibold prose-headings:text-foreground prose-headings:mt-3 prose-headings:mb-1.5 prose-headings:first:mt-0",
  "prose-p:my-1.5 prose-p:leading-relaxed prose-p:text-foreground prose-p:first:mt-0 prose-p:last:mb-0",
  "prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-li:marker:text-muted-foreground",
  "prose-strong:font-semibold prose-strong:text-foreground",
  "prose-a:text-primary prose-a:underline-offset-2 hover:prose-a:text-primary/80",
  "prose-blockquote:my-2 prose-blockquote:border-l-2 prose-blockquote:border-primary/40 prose-blockquote:font-normal prose-blockquote:not-italic prose-blockquote:text-muted-foreground",
  "prose-hr:my-3 prose-hr:border-border",
  "prose-code:rounded-sm prose-code:bg-foreground/10 prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.8em] prose-code:font-normal prose-code:text-foreground prose-code:before:content-none prose-code:after:content-none",
  "prose-pre:my-2 prose-pre:rounded-md prose-pre:border prose-pre:border-border prose-pre:bg-background prose-pre:font-mono prose-pre:text-foreground",
  "prose-table:my-2 prose-th:border prose-th:border-border prose-th:bg-background prose-th:px-2 prose-th:py-1 prose-th:text-foreground",
  "prose-td:border prose-td:border-border prose-td:px-2 prose-td:py-1",
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0",
  "[&_tbody_tr:nth-child(even)]:bg-foreground/5"
);

export function MarkdownContent({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn(MARKDOWN_CLASSNAMES, className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}

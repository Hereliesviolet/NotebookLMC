import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Collapsible } from "@/components/ui/collapsible";
import { CitationCard } from "@/components/chat/CitationCard";
import { FollowUpChips } from "@/components/chat/FollowUpChips";
import type { Citation, Confidence, MessageRole } from "@/lib/types";

interface MessageBubbleProps {
  role: MessageRole;
  content: string;
  citations?: Citation[];
  confidence?: Confidence;
  followUpQuestions?: string[];
  onFollowUp?: (question: string) => void;
}

const CONFIDENCE_VARIANT: Record<Confidence, "success" | "warning" | "destructive"> = {
  high: "success",
  medium: "warning",
  low: "destructive",
};

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

export function MessageBubble({
  role,
  content,
  citations = [],
  confidence,
  followUpQuestions = [],
  onFollowUp,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={cn("flex flex-col gap-2", isUser && "items-end")}>
      <div
        className={cn(
          "max-w-2xl rounded-lg px-4 py-2.5 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className={MARKDOWN_CLASSNAMES}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
        {confidence && (
          <div className="mt-2">
            <Badge variant={CONFIDENCE_VARIANT[confidence]}>Konfidenz: {confidence}</Badge>
          </div>
        )}
      </div>

      {citations.length > 0 && (
        <Collapsible
          className="w-full max-w-2xl"
          trigger={(open) => <span>{open ? "Quellen ausblenden" : `Quellen anzeigen (${citations.length})`}</span>}
        >
          <div className="grid gap-2 sm:grid-cols-2">
            {citations.map((citation, index) => (
              <CitationCard key={`${citation.chunk_id}-${index}`} citation={citation} index={index} />
            ))}
          </div>
        </Collapsible>
      )}

      {followUpQuestions.length > 0 && onFollowUp && (
        <FollowUpChips questions={followUpQuestions} onSelect={onFollowUp} />
      )}
    </div>
  );
}

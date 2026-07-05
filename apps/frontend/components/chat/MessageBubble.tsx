import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
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
        <p className="whitespace-pre-wrap">{content}</p>
        {confidence && (
          <div className="mt-2">
            <Badge variant={CONFIDENCE_VARIANT[confidence]}>Konfidenz: {confidence}</Badge>
          </div>
        )}
      </div>

      {citations.length > 0 && (
        <div className="grid w-full max-w-2xl gap-2 sm:grid-cols-2">
          {citations.map((citation, index) => (
            <CitationCard key={`${citation.chunk_id}-${index}`} citation={citation} index={index} />
          ))}
        </div>
      )}

      {followUpQuestions.length > 0 && onFollowUp && (
        <FollowUpChips questions={followUpQuestions} onSelect={onFollowUp} />
      )}
    </div>
  );
}

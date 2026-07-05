"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { listMessages, sendChatMessage } from "@/lib/api-client";
import type { Citation, Confidence, MessageRole } from "@/lib/types";

interface DisplayMessage {
  role: MessageRole;
  content: string;
  citations?: Citation[];
  confidence?: Confidence;
  followUpQuestions?: string[];
}

export function ChatPanel({ notebookId }: { notebookId: string }) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listMessages(notebookId)
      .then((history) =>
        setMessages(
          history.map((m) => ({
            role: m.role,
            content: m.content,
            citations: m.citations_json ?? undefined,
          }))
        )
      )
      .catch(() => undefined);
  }, [notebookId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    const question = text.trim();
    if (!question || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const response = await sendChatMessage(notebookId, question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          confidence: response.confidence,
          followUpQuestions: response.follow_up_questions,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Antwort konnte nicht generiert werden.");
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    sendMessage(input);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Stelle eine Frage zu den hochgeladenen Quellen. Antworten sind ausschließlich quellenbasiert.
          </p>
        )}
        {messages.map((message, index) => (
          <MessageBubble
            key={index}
            role={message.role}
            content={message.content}
            citations={message.citations}
            confidence={message.confidence}
            followUpQuestions={message.followUpQuestions}
            onFollowUp={sendMessage}
          />
        ))}
        {sending && <p className="text-xs text-muted-foreground">Antwort wird generiert…</p>}
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-border p-4">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Frage zu deinen Quellen stellen…"
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage(input);
            }
          }}
        />
        <Button type="submit" disabled={sending || !input.trim()} size="icon">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}

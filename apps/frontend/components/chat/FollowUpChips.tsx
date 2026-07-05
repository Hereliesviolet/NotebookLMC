export function FollowUpChips({
  questions,
  onSelect,
}: {
  questions: string[];
  onSelect: (question: string) => void;
}) {
  if (!questions.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {questions.map((question) => (
        <button
          key={question}
          onClick={() => onSelect(question)}
          className="rounded-full border border-border px-3 py-1.5 text-xs hover:bg-muted"
        >
          {question}
        </button>
      ))}
    </div>
  );
}

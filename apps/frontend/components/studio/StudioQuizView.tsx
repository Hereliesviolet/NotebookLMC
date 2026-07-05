"use client";

import { useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StudioQuizContent } from "@/lib/types";

export function StudioQuizView({ content }: { content: StudioQuizContent }) {
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [correctCount, setCorrectCount] = useState(0);

  const questions = content.questions;

  if (questions.length === 0) {
    return <p className="text-sm text-muted-foreground">Keine Fragen gefunden.</p>;
  }

  const finished = index >= questions.length;

  function handleRestart() {
    setIndex(0);
    setSelected(null);
    setCorrectCount(0);
  }

  if (finished) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-md border border-border p-8 text-center">
        <p className="text-sm text-muted-foreground">Quiz abgeschlossen</p>
        <p className="text-3xl font-semibold text-foreground">
          {correctCount} von {questions.length} richtig
        </p>
        <Button onClick={handleRestart}>
          <RotateCcw className="h-4 w-4" />
          Neu starten
        </Button>
      </div>
    );
  }

  const question = questions[index];

  function handleSelect(optionIndex: number) {
    if (selected !== null) return;
    setSelected(optionIndex);
    if (optionIndex === question.correct_index) {
      setCorrectCount((count) => count + 1);
    }
  }

  function handleNext() {
    setSelected(null);
    setIndex((value) => value + 1);
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <p className="text-xs font-medium text-muted-foreground">
        Frage {index + 1} von {questions.length}
      </p>
      <p className="text-lg font-semibold text-foreground">{question.question}</p>

      <div className="flex flex-col gap-2">
        {question.options.map((option, optionIndex) => {
          const isCorrect = optionIndex === question.correct_index;
          const isSelected = optionIndex === selected;
          const showResult = selected !== null;
          return (
            <button
              key={optionIndex}
              type="button"
              onClick={() => handleSelect(optionIndex)}
              disabled={showResult}
              className={cn(
                "flex items-center justify-between gap-2 rounded-md border border-border px-4 py-3 text-left text-sm transition-colors",
                !showResult && "hover:border-primary hover:bg-primary/5",
                showResult && isCorrect && "border-emerald-500 bg-emerald-50 text-emerald-700",
                showResult && isSelected && !isCorrect && "border-red-500 bg-red-50 text-red-700"
              )}
            >
              <span>{option}</span>
              {showResult && isCorrect && <Check className="h-4 w-4 shrink-0" />}
              {showResult && isSelected && !isCorrect && <X className="h-4 w-4 shrink-0" />}
            </button>
          );
        })}
      </div>

      {selected !== null && (
        <div className="rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          {question.explanation}
        </div>
      )}

      {selected !== null && (
        <Button onClick={handleNext} className="self-end">
          {index + 1 === questions.length ? "Ergebnis anzeigen" : "Weiter"}
        </Button>
      )}
    </div>
  );
}

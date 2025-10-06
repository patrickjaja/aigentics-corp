"use client";

import * as React from "react";
import { ChevronRight, ChevronLeft, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { Question } from "@/types/api";

interface QuestionFlowProps {
  conversationId: string;
  onComplete?: (answers: Record<string, unknown>) => void;
  maxQuestionsVisible?: number;
  className?: string;
}

export function QuestionFlow({
  conversationId,
  onComplete,
  maxQuestionsVisible = 5,
  className,
}: QuestionFlowProps) {
  const [questions, setQuestions] = React.useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const [answers, setAnswers] = React.useState<Record<string, unknown>>({});
  const [isLoading, setIsLoading] = React.useState(true);

  // Load questions on mount
  React.useEffect(() => {
    loadQuestions();
  }, [conversationId]);

  const loadQuestions = async () => {
    try {
      const response = await fetch(
        `/api/v1/conversations/${conversationId}/questions`
      );

      if (!response.ok) throw new Error("Failed to load questions");

      const data = await response.json();
      setQuestions(data.questions || []);
    } catch (error) {
      console.error("Failed to load questions:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswer = (questionId: string, value: unknown) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));

    // Mark question as answered
    setQuestions((prev) =>
      prev.map((q) =>
        q.id === questionId ? { ...q, answered: true, answer: value } : q
      )
    );
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  const handleComplete = async () => {
    try {
      const response = await fetch(
        `/api/v1/conversations/${conversationId}/answers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ answers }),
        }
      );

      if (!response.ok) throw new Error("Failed to submit answers");

      onComplete?.(answers);
    } catch (error) {
      console.error("Failed to submit answers:", error);
    }
  };

  const visibleQuestions = questions.slice(
    Math.max(0, currentIndex - Math.floor(maxQuestionsVisible / 2)),
    Math.min(
      questions.length,
      currentIndex + Math.ceil(maxQuestionsVisible / 2)
    )
  );

  const currentQuestion = questions[currentIndex];
  const progress = questions.length > 0
    ? ((currentIndex + 1) / questions.length) * 100
    : 0;
  const canProceed = currentQuestion
    ? !currentQuestion.required || currentQuestion.answered
    : false;

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <p>Fragen werden geladen...</p>
        </CardContent>
      </Card>
    );
  }

  if (questions.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <p>Keine Fragen verfügbar.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Projektanforderungen</span>
          <span className="text-sm font-normal text-muted-foreground">
            {currentIndex + 1} / {questions.length}
          </span>
        </CardTitle>
        {/* Progress Bar */}
        <div className="w-full bg-muted rounded-full h-2 mt-2">
          <div
            className="bg-primary h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Question Navigation Breadcrumb */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {visibleQuestions.map((q, idx) => {
            const absoluteIndex =
              Math.max(0, currentIndex - Math.floor(maxQuestionsVisible / 2)) +
              idx;
            const isCurrent = absoluteIndex === currentIndex;
            const isAnswered = q.answered;

            return (
              <React.Fragment key={q.id}>
                <button
                  onClick={() => setCurrentIndex(absoluteIndex)}
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors",
                    isCurrent
                      ? "border-primary bg-primary text-primary-foreground"
                      : isAnswered
                        ? "border-green-500 bg-green-500 text-white"
                        : "border-muted-foreground/30 bg-background"
                  )}
                >
                  {isAnswered && !isCurrent ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span className="text-sm">{absoluteIndex + 1}</span>
                  )}
                </button>
                {idx < visibleQuestions.length - 1 && (
                  <div className="h-0.5 w-4 bg-muted-foreground/30" />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Current Question */}
        {currentQuestion && (
          <div className="space-y-4">
            <div>
              <Label className="text-base font-semibold">
                {currentQuestion.text}
                {currentQuestion.required && (
                  <span className="text-destructive ml-1">*</span>
                )}
              </Label>
            </div>

            {/* Question Input based on type */}
            {currentQuestion.type === "text" && (
              <Textarea
                value={(answers[currentQuestion.id] as string) || ""}
                onChange={(e) => handleAnswer(currentQuestion.id, e.target.value)}
                placeholder="Ihre Antwort..."
                rows={4}
              />
            )}

            {currentQuestion.type === "select" && currentQuestion.options && (
              <Select
                value={(answers[currentQuestion.id] as string) || ""}
                onValueChange={(value) => handleAnswer(currentQuestion.id, value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Bitte wählen Sie..." />
                </SelectTrigger>
                <SelectContent>
                  {currentQuestion.options.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            {currentQuestion.type === "number" && (
              <Input
                type="number"
                value={(answers[currentQuestion.id] as number) || ""}
                onChange={(e) =>
                  handleAnswer(currentQuestion.id, parseInt(e.target.value, 10))
                }
                placeholder="Geben Sie eine Zahl ein..."
              />
            )}
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between pt-4">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Zurück
          </Button>
          <Button onClick={handleNext} disabled={!canProceed}>
            {currentIndex === questions.length - 1 ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Abschließen
              </>
            ) : (
              <>
                Weiter
                <ChevronRight className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

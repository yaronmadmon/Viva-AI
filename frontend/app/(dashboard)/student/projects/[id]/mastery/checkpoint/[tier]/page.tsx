"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useStartCheckpoint, useSubmitCheckpoint } from "@/hooks/use-mastery";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function CheckpointPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const tierStr = params?.tier as string;
  const tier = parseInt(tierStr ?? "0", 10);
  const [started, setStarted] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{
    passed: boolean;
    score_percentage: number;
    correct_answers: number;
    total_questions: number;
  } | null>(null);
  const { data: project } = useProject(projectId);
  const startMutation = useStartCheckpoint(projectId, tier);
  const submitMutation = useSubmitCheckpoint(projectId, tier);

  async function handleStart() {
    try {
      await startMutation.mutateAsync();
      setStarted(true);
    } catch {
      // error
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const questions = startMutation.data?.questions ?? [];
    try {
      const res = await submitMutation.mutateAsync({
        answers: questions.map((q) => ({
          question_id: q.id,
          user_answer: answers[q.id] ?? "",
          word_count: tier === 2 ? (answers[q.id]?.trim().split(/\s+/).length ?? 0) : undefined,
        })),
        time_spent_seconds: 0,
      });
      setResult({
        passed: res.passed,
        score_percentage: res.score_percentage,
        correct_answers: res.correct_answers,
        total_questions: res.total_questions,
      });
    } catch {
      // error
    }
  }

  if (!project) {
    return <div className="p-6">Loading…</div>;
  }

  const questions = startMutation.data?.questions ?? [];

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">{project.title}</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}/mastery`} className="hover:underline">Mastery</Link>
        <span>/</span>
        <span>Tier {tier}</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Tier {tier} checkpoint</CardTitle></CardHeader>
        <CardContent>
          {!started ? (
            <Button onClick={handleStart} disabled={startMutation.isPending}>
              {startMutation.isPending ? "Loading…" : "Start checkpoint"}
            </Button>
          ) : result !== null ? (
            <div className="space-y-2">
              <p>{result.passed ? "Passed" : "Not passed"}</p>
              <p>Score: {result.correct_answers}/{result.total_questions} ({result.score_percentage.toFixed(0)}%)</p>
              <Button asChild><Link href={`/student/projects/${projectId}/mastery`}>Back to mastery</Link></Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {questions.map((q) => (
                <div key={q.id} className="space-y-2">
                  <Label>{q.text}</Label>
                  {tier === 2 ? (
                    <textarea
                      className="min-h-[100px] w-full rounded-md border px-3 py-2"
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                    />
                  ) : (
                    <Input
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                      placeholder="Your answer"
                    />
                  )}
                </div>
              ))}
              <Button type="submit" disabled={submitMutation.isPending}>
                {submitMutation.isPending ? "Submitting…" : "Submit"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

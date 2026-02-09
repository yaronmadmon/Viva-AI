"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useMasteryProgress } from "@/hooks/use-mastery";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function MasteryPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: progress, isLoading } = useMasteryProgress(projectId);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">
          {project?.title ?? projectId}
        </Link>
        <span>/</span>
        <span>Mastery</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Mastery progress</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : progress ? (
            <div className="space-y-2">
              <p>Current tier: {progress.current_tier}</p>
              <p>AI level: {progress.ai_level}</p>
              <p>Words written: {progress.total_words_written}</p>
              <p>Next checkpoint: {progress.next_checkpoint ?? "None"}</p>
              <div className="mt-4 flex gap-2">
                {[1, 2, 3].map((tier) => (
                  <Button key={tier} asChild>
                    <Link href={`/student/projects/${projectId}/mastery/checkpoint/${tier}`}>
                      Tier {tier} checkpoint
                    </Link>
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">No progress data.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

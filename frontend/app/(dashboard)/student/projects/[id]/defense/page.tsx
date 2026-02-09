"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProject } from "@/hooks/use-projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DefensePage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: defense, isLoading } = useQuery({
    queryKey: ["defense", projectId],
    queryFn: () =>
      api<{ project_id: string; mode: string; questions: { id: string; text: string; tier?: number }[] }>(
        `projects/${projectId}/defense/practice/questions`
      ),
    enabled: !!projectId,
  });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">{project?.title ?? projectId}</Link>
        <span>/</span>
        <span>Defense practice</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Practice questions</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <p className="text-muted-foreground">Loading…</p> : (
            <ul className="list-disc space-y-2 pl-4">
              {defense?.questions?.map((q) => (
                <li key={q.id}>{q.text}</li>
              )) ?? <p className="text-muted-foreground">No questions.</p>}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

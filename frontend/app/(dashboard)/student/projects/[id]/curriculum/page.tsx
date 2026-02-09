"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useProject } from "@/hooks/use-projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CurriculumPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: conceptsData, isLoading: conceptsLoading } = useQuery({
    queryKey: ["curriculum", "concepts", projectId],
    queryFn: async () => {
      const res = await apiFetch(`projects/${projectId}/curriculum/concepts?discipline=stem`);
      if (!res.ok) return { data: { project_id: projectId, discipline: "stem", concepts: [] as unknown[] }, ok: false };
      const j = await res.json();
      return { data: j as { project_id: string; discipline: string; concepts: unknown[] }, ok: true };
    },
    enabled: !!projectId,
  });
  const { data: lessonsData, isLoading: lessonsLoading } = useQuery({
    queryKey: ["curriculum", "lessons", projectId],
    queryFn: async () => {
      const res = await apiFetch(`projects/${projectId}/curriculum/lessons?discipline=stem`);
      if (!res.ok) return { data: { project_id: projectId, discipline: "stem", lessons: {} as unknown }, ok: false };
      const j = await res.json();
      return { data: j as { project_id: string; discipline: string; lessons: unknown }, ok: true };
    },
    enabled: !!projectId,
  });

  const concepts = conceptsData?.data;
  const lessons = lessonsData?.data;
  const unavailable = (conceptsData?.ok === false) || (lessonsData?.ok === false);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">{project?.title ?? projectId}</Link>
        <span>/</span>
        <span>Curriculum</span>
      </div>
      {unavailable && (
        <p className="mb-4 text-sm text-muted-foreground">
          Curriculum data is not available for this project. You may need to be logged in or the backend may not support this yet.
        </p>
      )}
      <Card>
        <CardHeader><CardTitle>Concepts</CardTitle></CardHeader>
        <CardContent>
          {conceptsLoading ? <p className="text-muted-foreground">Loading…</p> : (
            <pre className="text-xs overflow-auto">{JSON.stringify(concepts?.concepts ?? [], null, 2)}</pre>
          )}
        </CardContent>
      </Card>
      <Card className="mt-4">
        <CardHeader><CardTitle>Lessons</CardTitle></CardHeader>
        <CardContent>
          {lessonsLoading ? <p className="text-muted-foreground">Loading…</p> : (
            <pre className="text-xs overflow-auto">{JSON.stringify(lessons?.lessons ?? {}, null, 2)}</pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

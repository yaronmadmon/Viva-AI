"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProject } from "@/hooks/use-projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CertificationPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: cert, isLoading } = useQuery({
    queryKey: ["certification", projectId],
    queryFn: () =>
      api<{ project_id: string; ready: boolean; components: Record<string, boolean> }>(
        `projects/${projectId}/certification`
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
        <span>Certification</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Certification status</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <p className="text-muted-foreground">Loading…</p> : (
            <div>
              <p>Ready: {cert?.ready ? "Yes" : "No"}</p>
              <p className="text-sm text-muted-foreground">Components: {JSON.stringify(cert?.components ?? {})}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

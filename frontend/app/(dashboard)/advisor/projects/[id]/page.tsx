"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdvisorProjectPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project, isLoading } = useProject(projectId);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/advisor" className="hover:underline">Review queue</Link>
        <span>/</span>
        <Link href="/advisor/projects" className="hover:underline">Projects</Link>
        <span>/</span>
        <span>{project?.title ?? projectId}</span>
      </div>
      <Card>
        <CardHeader><CardTitle>{project?.title ?? "Project"}</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <p className="text-muted-foreground">Loading…</p> : (
            <Button asChild>
              <Link href={`/advisor/projects/${projectId}/submission-units`}>
                View submission units
              </Link>
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

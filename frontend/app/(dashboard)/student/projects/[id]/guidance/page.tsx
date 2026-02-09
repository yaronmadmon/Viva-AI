"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useGuidanceNext } from "@/hooks/use-guidance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function GuidancePage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: guidance, isLoading } = useGuidanceNext(projectId);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">{project?.title ?? projectId}</Link>
        <span>/</span>
        <span>Guidance</span>
      </div>
      <Card>
        <CardHeader><CardTitle>What to do next</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <p className="text-muted-foreground">Loading…</p> : (
            <ul className="space-y-2">
              {guidance?.rules?.map((r) => (
                <li key={r.id} className="flex items-center gap-2">
                  <span>{r.message}</span>
                  {r.cta && (
                    <Button size="sm" asChild>
                      <Link href={r.cta_path ? `/student/projects/${projectId}/${r.cta_path}` : `/student/projects/${projectId}/mastery`}>
                        {r.cta}
                      </Link>
                    </Button>
                  )}
                </li>
              )) ?? <p className="text-muted-foreground">No guidance rules.</p>}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

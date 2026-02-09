"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useSubmissionUnits } from "@/hooks/use-submission-units";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdvisorSubmissionUnitsPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: units, isLoading } = useSubmissionUnits(projectId);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/advisor" className="hover:underline">Review queue</Link>
        <span>/</span>
        <Link href={`/advisor/projects/${projectId}`} className="hover:underline">{project?.title ?? projectId}</Link>
        <span>/</span>
        <span>Submission units</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Submission units</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <p className="text-muted-foreground">Loading…</p> : !units?.length ? (
            <p className="text-muted-foreground">No units in this project.</p>
          ) : (
            <ul className="space-y-2">
              {units.map((u) => (
                <li key={u.id}>
                  <Link
                    href={`/advisor/projects/${projectId}/submission-units/${u.id}`}
                    className="block rounded border p-3 hover:bg-muted/50"
                  >
                    <span className="font-medium">{u.title}</span>
                    <span className="ml-2 text-sm text-muted-foreground">— {u.state}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

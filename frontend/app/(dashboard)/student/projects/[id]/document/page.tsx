"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useProjectDocument } from "@/hooks/use-artifacts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DocumentPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: doc, isLoading } = useProjectDocument(projectId);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">
          Dashboard
        </Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">
          {project?.title ?? projectId}
        </Link>
        <span>/</span>
        <span>Document</span>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{project?.title ?? "Document"}</CardTitle>
          <p className="text-sm text-muted-foreground">
            Full project content in order. Edit individual artifacts from the Artifacts tab.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading ? (
            <p className="text-muted-foreground">Loading document…</p>
          ) : !doc?.artifacts?.length ? (
            <p className="text-muted-foreground">
              No artifacts yet. Add artifacts from the project workspace to see them here.
            </p>
          ) : (
            doc.artifacts.map((chunk) => (
              <section
                key={chunk.id}
                id={`artifact-${chunk.id}`}
                className="border-b pb-4 last:border-b-0 last:pb-0"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    {chunk.artifact_type}
                  </span>
                  <Link
                    href={`/student/projects/${projectId}/artifacts/${chunk.id}`}
                    className="text-xs text-primary hover:underline"
                  >
                    Edit
                  </Link>
                </div>
                {chunk.title && (
                  <h3 className="text-lg font-semibold mb-1">{chunk.title}</h3>
                )}
                <div className="prose prose-sm max-w-none whitespace-pre-wrap text-foreground">
                  {chunk.content || <span className="text-muted-foreground italic">No content</span>}
                </div>
              </section>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useArtifactTree } from "@/hooks/use-artifacts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function flattenTree(
  nodes: { id: string; artifact_type: string; title: string | null; children: unknown[] }[],
  out: { id: string; type: string; title: string }[] = []
): { id: string; type: string; title: string }[] {
  for (const n of nodes) {
    out.push({ id: n.id, type: n.artifact_type, title: n.title ?? "(untitled)" });
    if (Array.isArray(n.children) && n.children.length)
      flattenTree(n.children as { id: string; artifact_type: string; title: string | null; children: unknown[] }[], out);
  }
  return out;
}

export default function GraphPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const { data: project } = useProject(projectId);
  const { data: tree, isLoading } = useArtifactTree(projectId);
  const flat = tree ? flattenTree(tree.root_artifacts) : [];

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">{project?.title ?? projectId}</Link>
        <span>/</span>
        <span>Graph</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Artifact graph</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : flat.length === 0 ? (
            <p className="text-muted-foreground">No artifacts. Add artifacts to see claim–evidence structure.</p>
          ) : (
            <ul className="space-y-1">
              {flat.map((a) => (
                <li key={a.id}>
                  <Link
                    href={`/student/projects/${projectId}/artifacts/${a.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    <span className="font-medium text-muted-foreground">[{a.type}]</span> {a.title}
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

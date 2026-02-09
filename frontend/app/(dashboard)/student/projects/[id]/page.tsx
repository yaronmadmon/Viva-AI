"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useProject, useGenerationStatus, useGenerateProject } from "@/hooks/use-projects";
import { useArtifactTree } from "@/hooks/use-artifacts";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function ArtifactTreeList({
  projectId,
  nodes,
  depth = 0,
}: {
  projectId: string;
  nodes: { id: string; artifact_type: string; title: string | null; children: unknown[] }[];
  depth?: number;
}) {
  return (
    <ul className={depth ? "ml-4 border-l pl-2" : ""}>
      {nodes.map((n) => (
        <li key={n.id} className="py-1">
          <Link
            href={`/student/projects/${projectId}/artifacts/${n.id}`}
            className="text-sm text-primary hover:underline"
          >
            [{n.artifact_type}] {n.title || "(untitled)"}
          </Link>
          {Array.isArray(n.children) && n.children.length > 0 && (
            <ArtifactTreeList
              projectId={projectId}
              nodes={n.children as { id: string; artifact_type: string; title: string | null; children: unknown[] }[]}
              depth={depth + 1}
            />
          )}
        </li>
      ))}
    </ul>
  );
}

function GenerationBanner({
  projectId,
}: {
  projectId: string;
}) {
  const { data: genStatus, isLoading } = useGenerationStatus(projectId);
  const generateProject = useGenerateProject();

  if (isLoading || !genStatus) return null;

  if (genStatus.all_generated) {
    return (
      <Card className="mb-4 border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950">
        <CardContent className="flex items-center gap-3 py-3">
          <span className="text-lg">&#10003;</span>
          <div className="flex-1">
            <p className="text-sm font-medium text-green-800 dark:text-green-200">
              Dissertation generated &mdash; {genStatus.total_words.toLocaleString()} words across{" "}
              {genStatus.total_sections} sections
            </p>
            <p className="text-xs text-green-700 dark:text-green-300">
              Content sourced from real academic papers. Click any section to review and edit.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => generateProject.mutate(projectId)}
            disabled={generateProject.isPending}
          >
            {generateProject.isPending ? "Regenerating..." : "Regenerate"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Generation in progress
  const pct =
    genStatus.total_sections > 0
      ? Math.round((genStatus.generated_sections / genStatus.total_sections) * 100)
      : 0;

  return (
    <Card className="mb-4 border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
      <CardContent className="py-3">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
            Generating PhD dissertation content...
          </p>
          <span className="text-xs text-blue-600 dark:text-blue-300">
            {genStatus.generated_sections}/{genStatus.total_sections} sections ({pct}%)
          </span>
        </div>
        <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
          <div
            className="bg-blue-600 dark:bg-blue-400 h-2 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="mt-2 space-y-1">
          {genStatus.sections.map((s) => (
            <div key={s.title} className="flex items-center gap-2 text-xs">
              <span
                className={
                  s.is_generated
                    ? "text-green-600 dark:text-green-400"
                    : "text-blue-400 dark:text-blue-500 animate-pulse"
                }
              >
                {s.is_generated ? "\u2713" : "\u25CB"}
              </span>
              <span className={s.is_generated ? "text-green-700 dark:text-green-300" : "text-blue-600 dark:text-blue-300"}>
                {s.title}
              </span>
              {s.is_generated && (
                <span className="text-muted-foreground">({s.word_count.toLocaleString()} words)</span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = params?.id as string | undefined;
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: project, isLoading: projectLoading } = useProject(projectId ?? null);
  const { data: tree, isLoading: treeLoading } = useArtifactTree(projectId ?? null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  if (!projectId) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Invalid project.</p>
      </div>
    );
  }

  if (projectLoading || !project) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  const disciplineLabels: Record<string, string> = {
    stem: "STEM",
    humanities: "Humanities",
    social_sciences: "Social Sciences",
    legal: "Legal",
    mixed: "Mixed / Interdisciplinary",
  };

  return (
    <div className="p-6">
      <header className="mb-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="/student" className="hover:underline">
            Dashboard
          </Link>
          <span>/</span>
          <span>{project.title}</span>
        </div>
        <h1 className="mt-1 text-xl font-semibold">{project.title}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
            {disciplineLabels[project.discipline_type] || project.discipline_type}
          </span>
          <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs font-medium">
            {project.status}
          </span>
          <span>{project.artifact_count} section(s)</span>
          {project.integrity_score > 0 && (
            <span>Integrity: {(project.integrity_score * 100).toFixed(0)}%</span>
          )}
        </div>
        {project.description && (
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{project.description}</p>
        )}
      </header>

      {/* Generation status banner */}
      <GenerationBanner projectId={projectId} />

      <Tabs defaultValue="artifacts">
        <TabsList className="flex-wrap">
          <TabsTrigger value="artifacts">Sections</TabsTrigger>
          <TabsTrigger value="document" asChild>
            <Link href={`/student/projects/${projectId}/document`}>Full Document</Link>
          </TabsTrigger>
          <TabsTrigger value="graph" asChild>
            <Link href={`/student/projects/${projectId}/graph`}>Graph</Link>
          </TabsTrigger>
          <TabsTrigger value="submission-units" asChild>
            <Link href={`/student/projects/${projectId}/submission-units`}>Submission units</Link>
          </TabsTrigger>
          <TabsTrigger value="curriculum" asChild>
            <Link href={`/student/projects/${projectId}/curriculum`}>Curriculum</Link>
          </TabsTrigger>
          <TabsTrigger value="mastery" asChild>
            <Link href={`/student/projects/${projectId}/mastery`}>Mastery</Link>
          </TabsTrigger>
          <TabsTrigger value="guidance" asChild>
            <Link href={`/student/projects/${projectId}/guidance`}>Guidance</Link>
          </TabsTrigger>
          <TabsTrigger value="certification" asChild>
            <Link href={`/student/projects/${projectId}/certification`}>Certification</Link>
          </TabsTrigger>
          <TabsTrigger value="quality" asChild>
            <Link href={`/student/projects/${projectId}/quality`}>Quality Report</Link>
          </TabsTrigger>
          <TabsTrigger value="defense" asChild>
            <Link href={`/student/projects/${projectId}/defense`}>Defense</Link>
          </TabsTrigger>
          <TabsTrigger value="export" asChild>
            <Link href={`/student/projects/${projectId}/export`}>Export</Link>
          </TabsTrigger>
        </TabsList>
        <TabsContent value="artifacts" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Dissertation Sections</CardTitle>
              <Button
                type="button"
                onClick={() => router.push(`/student/projects/${projectId}/artifacts/new`)}
              >
                New section
              </Button>
            </CardHeader>
            <CardContent>
              {treeLoading ? (
                <p className="text-muted-foreground">Loading tree...</p>
              ) : !tree?.root_artifacts?.length ? (
                <p className="text-muted-foreground">No sections yet. Create one to get started.</p>
              ) : (
                <ArtifactTreeList projectId={projectId} nodes={tree.root_artifacts} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

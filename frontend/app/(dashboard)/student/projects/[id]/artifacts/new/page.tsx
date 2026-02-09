"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useProject } from "@/hooks/use-projects";
import { useCreateArtifact } from "@/hooks/use-artifacts";
import { APIError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ARTIFACT_TYPES = [
  "section",
  "claim",
  "evidence",
  "source",
  "note",
  "method",
  "result",
  "discussion",
];

export default function NewArtifactPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const createArtifact = useCreateArtifact(projectId);
  const [artifactType, setArtifactType] = useState("section");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await createArtifact.mutateAsync({
        artifact_type: artifactType,
        title: title.trim() || undefined,
        content: content.trim() || "",
      });
      router.push(`/student/projects/${projectId}/artifacts/${created.id}`);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.detail);
      } else if (err instanceof TypeError && (err.message === "Failed to fetch" || err.message?.includes("network"))) {
        setError("Cannot reach the server. Is the backend running on http://localhost:8000?");
      } else {
        setError(err instanceof Error ? err.message : "Failed to create artifact.");
      }
    }
  }

  if (!user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (projectLoading || !project) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading project…</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <header className="mb-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="/student" className="hover:underline">
            Dashboard
          </Link>
          <span>/</span>
          <Link href={`/student/projects/${projectId}`} className="hover:underline">
            {project.title}
          </Link>
          <span>/</span>
          <span>New artifact</span>
        </div>
        <h1 className="mt-1 text-xl font-semibold">New artifact</h1>
      </header>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-4">
        <div className="space-y-2">
          <Label htmlFor="type">Type</Label>
          <Select value={artifactType} onValueChange={setArtifactType}>
            <SelectTrigger id="type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ARTIFACT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="title">Title (optional)</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Artifact title"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="content">Content</Label>
          <textarea
            id="content"
            className="min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Content..."
          />
        </div>
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        <div className="flex gap-2">
          <Button type="submit" disabled={createArtifact.isPending}>
            {createArtifact.isPending ? "Creating…" : "Create"}
          </Button>
          <Button type="button" variant="outline" asChild>
            <Link href={`/student/projects/${projectId}`}>Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}

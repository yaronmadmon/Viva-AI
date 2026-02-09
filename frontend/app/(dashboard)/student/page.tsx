"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useProjects, useCreateProject } from "@/hooks/use-projects";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DISCIPLINE_TYPES = [
  { value: "stem", label: "STEM" },
  { value: "humanities", label: "Humanities" },
  { value: "social_sciences", label: "Social Sciences" },
  { value: "legal", label: "Legal" },
  { value: "mixed", label: "Mixed / Interdisciplinary" },
];

export default function StudentPage() {
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [discipline, setDiscipline] = useState("mixed");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const u = getUser();
    if (u) {
      const role = (u.role || "").toLowerCase();
      if (role !== "student" && role !== "admin") {
        router.replace("/");
        return;
      }
    }
    setUser(u);
  }, [router]);

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setError(null);
    try {
      const created = await createProject.mutateAsync({
        title: newTitle.trim(),
        description: newDescription.trim() || undefined,
        discipline_type: discipline,
      });
      setNewTitle("");
      setNewDescription("");
      setDiscipline("mixed");
      setOpen(false);
      router.push(`/student/projects/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project.");
    }
  }

  return (
    <div className="p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Student Dashboard</h1>
          <p className="text-muted-foreground">
            {user ? (
              `Welcome, ${user.full_name}`
            ) : (
              <>
                <Link href="/login" className="text-primary underline hover:no-underline">
                  Log in
                </Link>
                {" to create and manage projects."}
              </>
            )}
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            {user ? (
              <Button>New project</Button>
            ) : (
              <Button variant="outline" asChild>
                <Link href="/login">New project (log in first)</Link>
              </Button>
            )}
          </DialogTrigger>
          <DialogContent aria-describedby="create-project-desc">
            <DialogHeader>
              <DialogTitle>Create research project</DialogTitle>
              <DialogDescription id="create-project-desc">
                Create your PhD research project. The system will search real academic papers and
                generate a complete dissertation with full citations, methodology, and analysis.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Project title</Label>
                <Input
                  id="title"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Impact of AI on Academic Integrity"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <textarea
                  id="description"
                  className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Brief description of your research focus, questions, or objectives..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="discipline">Discipline</Label>
                <Select value={discipline} onValueChange={setDiscipline}>
                  <SelectTrigger id="discipline">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DISCIPLINE_TYPES.map((d) => (
                      <SelectItem key={d.value} value={d.value}>
                        {d.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {error && (
                <p className="text-sm text-destructive" role="alert">{error}</p>
              )}
              <Button type="submit" className="w-full" disabled={createProject.isPending}>
                {createProject.isPending ? "Creating & generating..." : "Create & Generate PhD"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </header>

      {isLoading ? (
        <p className="text-muted-foreground">Loading projects…</p>
      ) : !projects?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>No projects yet</CardTitle>
            <CardDescription>
              {user
                ? "Create a project to start adding artifacts."
                : "Log in to create projects and add artifacts."}
            </CardDescription>
          </CardHeader>
          {!user && (
            <CardContent>
              <Button asChild>
                <Link href="/login">Log in to get started</Link>
              </Button>
            </CardContent>
          )}
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} href={`/student/projects/${p.id}`}>
              <Card className="transition-colors hover:bg-muted/50">
                <CardHeader>
                  <CardTitle className="truncate">{p.title}</CardTitle>
                  <CardDescription>
                    {p.artifact_count} artifact(s) · {p.discipline_type}
                  </CardDescription>
                </CardHeader>
                {p.description && (
                  <CardContent>
                    <p className="line-clamp-2 text-sm text-muted-foreground">{p.description}</p>
                  </CardContent>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

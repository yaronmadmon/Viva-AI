"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import {
  useSubmissionUnits,
  useCreateSubmissionUnit,
} from "@/hooks/use-submission-units";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SubmissionUnitsPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const [open, setOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const { data: project } = useProject(projectId);
  const { data: units, isLoading } = useSubmissionUnits(projectId);
  const createUnit = useCreateSubmissionUnit(projectId);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      await createUnit.mutateAsync({ title: newTitle.trim() });
      setNewTitle("");
      setOpen(false);
    } catch {
      // error from mutation
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">
          {project?.title ?? projectId}
        </Link>
        <span>/</span>
        <span>Submission units</span>
      </div>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Submission units</CardTitle>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>New unit</Button>
            </DialogTrigger>
            <DialogContent aria-describedby={undefined}>
              <DialogHeader><DialogTitle>Create submission unit</DialogTitle></DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Unit title"
                    required
                  />
                </div>
                <Button type="submit" disabled={createUnit.isPending}>
                  {createUnit.isPending ? "Creating…" : "Create"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : !units?.length ? (
            <p className="text-muted-foreground">No submission units. Create one to submit for review.</p>
          ) : (
            <ul className="space-y-2">
              {units.map((u) => (
                <li key={u.id}>
                  <Link
                    href={`/student/projects/${projectId}/submission-units/${u.id}`}
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

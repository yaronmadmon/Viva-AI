"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUser } from "@/lib/auth";
import { useProjects } from "@/hooks/use-projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ExaminerPage() {
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: projects, isLoading } = useProjects();

  useEffect(() => {
    setUser(getUser());
  }, []);

  return (
    <div className="p-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold">Examiner — Projects</h1>
        <p className="text-muted-foreground">
          {user ? "Assigned projects (frozen content view)" : "Log in to see assigned projects."}
        </p>
      </header>
      {isLoading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : !projects?.length ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">No projects assigned.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} href={`/examiner/projects/${p.id}`}>
              <Card className="transition-colors hover:bg-muted/50">
                <CardHeader>
                  <CardTitle className="truncate">{p.title}</CardTitle>
                  <p className="text-sm text-muted-foreground">{p.artifact_count} artifacts</p>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

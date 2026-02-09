"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useProjects } from "@/hooks/use-projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdvisorProjectsPage() {
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: projects, isLoading } = useProjects();

  useEffect(() => {
    const u = getUser();
    if (!u) {
      router.replace("/login");
      return;
    }
    setUser(u);
  }, [router]);

  if (!user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold">Projects</h1>
        <p className="text-muted-foreground">Projects shared with you (submission units)</p>
      </header>
      {isLoading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : !projects?.length ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">No projects shared with you.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} href={`/advisor/projects/${p.id}/submission-units`}>
              <Card className="transition-colors hover:bg-muted/50">
                <CardHeader>
                  <CardTitle className="truncate">{p.title}</CardTitle>
                  <p className="text-sm text-muted-foreground">{p.permission_level}</p>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

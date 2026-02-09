"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useFrozenContent } from "@/hooks/use-examiner";
import type { FrozenArtifact, FrozenUnit } from "@/hooks/use-examiner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ExaminerFrozenPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const [selected, setSelected] = useState<{ unit: FrozenUnit; artifact: FrozenArtifact } | null>(null);
  const { data: frozen, isLoading } = useFrozenContent(projectId);

  useEffect(() => {
    setUser(getUser());
  }, []);

  if (!user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/examiner" className="hover:underline">Projects</Link>
        <span>/</span>
        <span>{frozen?.project_title ?? projectId}</span>
      </div>
      <h1 className="mb-4 text-xl font-semibold">Frozen content (read-only)</h1>
      {isLoading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : !frozen?.units?.length ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">No locked/approved units for this project.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Units &amp; artifacts</CardTitle></CardHeader>
            <CardContent className="max-h-[60vh] overflow-auto">
              {frozen.units.map((unit) => (
                <div key={unit.id} className="mb-4">
                  <p className="font-medium">{unit.title}</p>
                  <p className="text-xs text-muted-foreground">{unit.state}</p>
                  <ul className="mt-1 space-y-1 pl-2">
                    {unit.artifacts.map((a) => (
                      <li key={a.id}>
                        <button
                          type="button"
                          className="text-left text-sm text-primary hover:underline"
                          onClick={() => setSelected({ unit, artifact: a })}
                        >
                          [{a.artifact_type}] {a.title || "(untitled)"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Content</CardTitle></CardHeader>
            <CardContent>
              {selected ? (
                <div>
                  <p className="text-sm text-muted-foreground">
                    {selected.artifact.artifact_type} · {selected.artifact.title || "(untitled)"}
                  </p>
                  <div className="mt-2 whitespace-pre-wrap rounded border bg-muted/30 p-3 text-sm">
                    {selected.artifact.content || "(empty)"}
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground">Select an artifact.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

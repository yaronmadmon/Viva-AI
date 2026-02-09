"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import { useIntegrityReport, useExportDocx } from "@/hooks/use-export";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ExportPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const [downloaded, setDownloaded] = useState(false);
  const { data: project } = useProject(projectId);
  const { data: integrity, isLoading } = useIntegrityReport(projectId);
  const exportDocx = useExportDocx(projectId);

  async function handleExport() {
    try {
      const blob = await exportDocx.mutateAsync();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `project-${projectId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      setDownloaded(true);
    } catch {
      // error
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/student" className="hover:underline">Dashboard</Link>
        <span>/</span>
        <Link href={`/student/projects/${projectId}`} className="hover:underline">{project?.title ?? projectId}</Link>
        <span>/</span>
        <span>Export</span>
      </div>
      <Card>
        <CardHeader><CardTitle>Integrity report</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : integrity ? (
            <div className="space-y-2">
              <p>Score: {integrity.overall_score}</p>
              <p>Export allowed: {integrity.export_allowed ? "Yes" : "No"}</p>
              {integrity.blocking_issues?.length ? (
                <p className="text-destructive">Blockers: {integrity.blocking_issues.join("; ")}</p>
              ) : null}
            </div>
          ) : (
            <p className="text-muted-foreground">No report.</p>
          )}
        </CardContent>
      </Card>
      <Card className="mt-4">
        <CardHeader><CardTitle>Export DOCX</CardTitle></CardHeader>
        <CardContent>
          <Button
            onClick={handleExport}
            disabled={exportDocx.isPending || (integrity && !integrity.export_allowed)}
          >
            {exportDocx.isPending ? "Exporting…" : downloaded ? "Download again" : "Download DOCX"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

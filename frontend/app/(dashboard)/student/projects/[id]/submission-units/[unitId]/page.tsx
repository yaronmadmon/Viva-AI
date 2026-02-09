"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useProject } from "@/hooks/use-projects";
import {
  useSubmissionUnit,
  useTransitionSubmissionUnitState,
} from "@/hooks/use-submission-units";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STUDENT_NEXT_STATES = ["ready_for_review"];

export default function SubmissionUnitDetailPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const unitId = params?.unitId as string;
  const [optimisticState, setOptimisticState] = useState<string | null>(null);
  const { data: project } = useProject(projectId);
  const { data: unit, isLoading } = useSubmissionUnit(projectId, unitId);
  const transition = useTransitionSubmissionUnitState(projectId, unitId);
  const displayState = optimisticState ?? unit?.state ?? "";

  const canSubmitForReview =
    displayState === "draft" || displayState === "revisions_required";

  async function handleTransition(to_state: string) {
    setOptimisticState(to_state);
    try {
      await transition.mutateAsync(to_state);
    } catch {
      setOptimisticState(null);
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
        <Link href={`/student/projects/${projectId}/submission-units`} className="hover:underline">
          Submission units
        </Link>
        <span>/</span>
        <span>{unit?.title ?? unitId}</span>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{unit?.title ?? "Unit"}</CardTitle>
          <p className="text-sm text-muted-foreground">State: {displayState}</p>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : (
            <>
              {unit?.artifact_ids?.length ? (
                <p className="text-sm text-muted-foreground">
                  Artifacts: {unit.artifact_ids.length}
                </p>
              ) : null}
              {canSubmitForReview && (
                <Button
                  className="mt-2"
                  onClick={() => handleTransition("ready_for_review")}
                  disabled={transition.isPending}
                >
                  {transition.isPending ? "Submitting…" : "Submit for review"}
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

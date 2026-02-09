"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SubmissionUnitResponse } from "@/lib/types";

export function useSubmissionUnits(projectId: string | null) {
  return useQuery({
    queryKey: ["submission-units", projectId],
    queryFn: () =>
      api<SubmissionUnitResponse[]>(`projects/${projectId}/submission-units`),
    enabled: !!projectId,
  });
}

export function useSubmissionUnit(projectId: string | null, unitId: string | null) {
  return useQuery({
    queryKey: ["submission-unit", projectId, unitId],
    queryFn: () =>
      api<SubmissionUnitResponse>(
        `projects/${projectId}/submission-units/${unitId}`
      ),
    enabled: !!projectId && !!unitId,
  });
}

export function useCreateSubmissionUnit(projectId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; artifact_ids?: string[] }) =>
      api<SubmissionUnitResponse>(`projects/${projectId}/submission-units`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["submission-units", projectId ?? ""] });
    },
  });
}

export function useTransitionSubmissionUnitState(
  projectId: string | null,
  unitId: string | null
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (to_state: string) =>
      api<SubmissionUnitResponse>(
        `projects/${projectId}/submission-units/${unitId}/state`,
        { method: "PATCH", body: JSON.stringify({ to_state }) }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["submission-units", projectId ?? ""] });
      queryClient.invalidateQueries({ queryKey: ["submission-unit", projectId ?? "", unitId ?? ""] });
    },
  });
}

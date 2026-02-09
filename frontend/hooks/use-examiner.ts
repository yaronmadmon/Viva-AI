"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface FrozenArtifact {
  id: string;
  title: string;
  content: string;
  artifact_type: string;
}

export interface FrozenUnit {
  id: string;
  title: string;
  state: string;
  artifacts: FrozenArtifact[];
}

export interface FrozenContentResponse {
  project_id: string;
  project_title: string;
  units: FrozenUnit[];
}

export function useFrozenContent(projectId: string | null) {
  return useQuery({
    queryKey: ["examiner", "frozen", projectId],
    queryFn: () =>
      api<FrozenContentResponse>(`examiner/projects/${projectId}/frozen-content`),
    enabled: !!projectId,
  });
}

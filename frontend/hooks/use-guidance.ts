"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { GuidanceNextResponse } from "@/lib/types";

export function useGuidanceNext(projectId: string | null) {
  return useQuery({
    queryKey: ["guidance", projectId],
    queryFn: () =>
      api<GuidanceNextResponse>(`projects/${projectId}/guidance/next`),
    enabled: !!projectId,
  });
}

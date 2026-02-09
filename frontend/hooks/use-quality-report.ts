"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FullQualityReportResponse } from "@/lib/types";

export function useQualityReport(projectId: string | null) {
  return useQuery({
    queryKey: ["quality-report", projectId],
    queryFn: () =>
      api<FullQualityReportResponse>(
        `projects/${projectId}/quality/full-report`
      ),
    enabled: !!projectId,
    staleTime: 60_000, // cache for 1 min (reports are expensive)
    retry: 1,
  });
}

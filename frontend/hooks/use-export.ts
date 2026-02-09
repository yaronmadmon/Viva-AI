"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { api, BASE_URL } from "@/lib/api";
import type { IntegrityReport } from "@/lib/types";

export function useIntegrityReport(projectId: string | null) {
  return useQuery({
    queryKey: ["integrity", projectId],
    queryFn: () =>
      api<IntegrityReport>(`projects/${projectId}/integrity`),
    enabled: !!projectId,
  });
}

export function useExportDocx(projectId: string | null) {
  return useMutation({
    mutationFn: async () => {
      const token = typeof window !== "undefined" ? localStorage.getItem("viva_access_token") : null;
      const res = await fetch(`${BASE_URL}/projects/${projectId}/export/docx`, {
        method: "POST",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) throw new Error(await res.text());
      return res.blob();
    },
  });
}

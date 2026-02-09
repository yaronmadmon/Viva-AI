"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/auth";
import { api } from "@/lib/api";
import type { ProjectListResponse, ProjectResponse, GenerationStatusResponse } from "@/lib/types";

export function useProjects() {
  const hasToken = typeof window !== "undefined" && !!getAccessToken();
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api<ProjectListResponse[]>("projects"),
    enabled: hasToken,
  });
}

export function useProject(projectId: string | null) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api<ProjectResponse>(`projects/${projectId}`),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; description?: string; discipline_type?: string }) =>
      api<ProjectResponse>("projects", { method: "POST", body: JSON.stringify({ ...body, discipline_type: body.discipline_type || "mixed" }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useGenerationStatus(projectId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["generation-status", projectId],
    queryFn: () => api<GenerationStatusResponse>(`projects/${projectId}/generation-status`),
    enabled: !!projectId && enabled,
    refetchInterval: (query) => {
      // Poll every 5 seconds while generation is in progress
      const data = query.state.data;
      if (data && !data.all_generated) return 5000;
      return false; // Stop polling when all generated
    },
  });
}

export function useGenerateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      api<{ message: string }>(`projects/${projectId}/generate`, { method: "POST" }),
    onSuccess: (_data, projectId) => {
      queryClient.invalidateQueries({ queryKey: ["generation-status", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

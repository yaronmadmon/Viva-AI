"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  ArtifactTreeResponse,
  ArtifactDetailResponse,
  ArtifactResponse,
  ProjectDocumentResponse,
} from "@/lib/types";

export function useArtifactTree(projectId: string | null) {
  return useQuery({
    queryKey: ["artifacts", "tree", projectId],
    queryFn: () =>
      api<ArtifactTreeResponse>(`artifacts/projects/${projectId}/tree`),
    enabled: !!projectId,
  });
}

export function useProjectDocument(projectId: string | null) {
  return useQuery({
    queryKey: ["project", "document", projectId],
    queryFn: () =>
      api<ProjectDocumentResponse>(`projects/${projectId}/document`),
    enabled: !!projectId,
  });
}

export function useArtifact(artifactId: string | null) {
  return useQuery({
    queryKey: ["artifact", artifactId],
    queryFn: () => api<ArtifactDetailResponse>(`artifacts/${artifactId}`),
    enabled: !!artifactId,
  });
}

export function useCreateArtifact(projectId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      artifact_type: string;
      title?: string;
      content?: string;
      parent_id?: string;
      position?: number;
    }) =>
      api<ArtifactResponse>(`artifacts/projects/${projectId}/artifacts`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifacts", "tree", projectId ?? ""] });
      queryClient.invalidateQueries({ queryKey: ["project", "document", projectId ?? ""] });
    },
  });
}

export function useUpdateArtifact(artifactId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title?: string; content?: string; position?: number }) =>
      api<ArtifactResponse>(`artifacts/${artifactId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifact", artifactId ?? ""] });
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["project", "document"] });
    },
  });
}

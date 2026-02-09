"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  MasteryProgressResponse,
  CheckpointStartResponse,
  CheckpointResultResponse,
  CapabilitiesResponse,
  AISuggestionGenerateResponse,
} from "@/lib/types";

export function useMasteryProgress(projectId: string | null) {
  return useQuery({
    queryKey: ["mastery", projectId],
    queryFn: () =>
      api<MasteryProgressResponse>(`projects/${projectId}/mastery/progress`),
    enabled: !!projectId,
  });
}

export function useMasteryCapabilities(projectId: string | null) {
  return useQuery({
    queryKey: ["mastery", "capabilities", projectId],
    queryFn: () =>
      api<CapabilitiesResponse>(`projects/${projectId}/mastery/capabilities`),
    enabled: !!projectId,
  });
}

export function useGenerateAISuggestion(projectId: string | null) {
  return useMutation({
    mutationFn: (body: {
      artifact_id: string;
      suggestion_type: string;
      additional_instructions?: string;
    }) =>
      api<AISuggestionGenerateResponse>(
        `projects/${projectId}/mastery/ai-suggestions/generate`,
        { method: "POST", body: JSON.stringify(body) }
      ),
  });
}

export function useAcceptAISuggestion(projectId: string | null) {
  return useMutation({
    mutationFn: (body: {
      suggestion_id: string;
      artifact_id: string;
      suggestion_type: string;
      modified_content?: string;
      modification_ratio?: number;
    }) =>
      api<{ status: string; suggestion_id: string }>(
        `projects/${projectId}/mastery/ai-suggestions/accept`,
        { method: "POST", body: JSON.stringify(body) }
      ),
  });
}

export function useRejectAISuggestion(projectId: string | null) {
  return useMutation({
    mutationFn: (body: {
      suggestion_id: string;
      artifact_id: string;
      suggestion_type: string;
    }) =>
      api<{ status: string; suggestion_id: string }>(
        `projects/${projectId}/mastery/ai-suggestions/reject`,
        { method: "POST", body: JSON.stringify(body) }
      ),
  });
}

export function useStartCheckpoint(projectId: string | null, tier: number) {
  return useMutation({
    mutationFn: () =>
      api<CheckpointStartResponse>(
        `projects/${projectId}/mastery/checkpoint/${tier}/start`,
        { method: "POST" }
      ),
  });
}

export function useSubmitCheckpoint(projectId: string | null, tier: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      answers: Array<{ question_id: string; user_answer: string; word_count?: number }>;
      time_spent_seconds?: number;
    }) =>
      api<CheckpointResultResponse>(
        `projects/${projectId}/mastery/checkpoint/${tier}/submit`,
        { method: "POST", body: JSON.stringify(body) }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mastery", projectId ?? ""] });
    },
  });
}

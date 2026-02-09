"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api, apiFetch } from "@/lib/api";
import type { AvatarChatResponse, AvatarHistoryResponse } from "@/lib/types";

/**
 * Send a message to the teaching avatar and get a reply.
 */
export function useAvatarChat(projectId: string | null) {
  return useMutation({
    mutationFn: async (message: string) => {
      if (!projectId) throw new Error("No project selected");
      return api<AvatarChatResponse>(
        `projects/${projectId}/avatar/chat`,
        {
          method: "POST",
          body: JSON.stringify({ message }),
        }
      );
    },
  });
}

/**
 * Fetch conversation history for the teaching avatar.
 */
export function useAvatarHistory(projectId: string | null) {
  return useQuery({
    queryKey: ["avatar-history", projectId],
    queryFn: async () => {
      if (!projectId) throw new Error("No project selected");
      return api<AvatarHistoryResponse>(
        `projects/${projectId}/avatar/history`
      );
    },
    enabled: !!projectId,
    staleTime: 0, // always refetch when chat opens
  });
}

/**
 * Request TTS audio from the backend (OpenAI TTS).
 * Returns a blob URL that can be played via an Audio element.
 */
export async function avatarSpeak(
  projectId: string,
  text: string,
): Promise<string> {
  const res = await apiFetch(
    `projects/${projectId}/avatar/speak`,
    {
      method: "POST",
      body: JSON.stringify({ text }),
    },
  );

  if (!res.ok) {
    throw new Error(`TTS failed: ${res.status}`);
  }

  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

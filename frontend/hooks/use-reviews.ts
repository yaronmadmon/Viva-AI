"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/auth";
import { api } from "@/lib/api";
import type { ReviewRequestResponse } from "@/lib/types";

export function useAdvisorReviews(statusFilter?: string) {
  const hasToken = typeof window !== "undefined" && !!getAccessToken();
  const params = statusFilter ? `?status_filter=${statusFilter}` : "";
  return useQuery({
    queryKey: ["advisor-reviews", statusFilter],
    queryFn: () => api<ReviewRequestResponse[]>(`advisors/reviews${params}`),
    enabled: hasToken,
  });
}

export function useRespondReview(reviewId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { status: string; response_message?: string }) =>
      api<ReviewRequestResponse>(`reviews/${reviewId}/respond`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["advisor-reviews"] });
      queryClient.invalidateQueries({ queryKey: ["review", reviewId ?? ""] });
    },
  });
}

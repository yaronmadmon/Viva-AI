"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ReviewRequestResponse } from "@/lib/types";
import { useRespondReview } from "@/hooks/use-reviews";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function AdvisorReviewDetailPage() {
  const params = useParams();
  const reviewId = params?.id as string;
  const router = useRouter();
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const [status, setStatus] = useState("approved");
  const [responseMessage, setResponseMessage] = useState("");
  const { data: review, isLoading } = useQuery({
    queryKey: ["review", reviewId],
    queryFn: async () => {
      const list = await api<ReviewRequestResponse[]>("advisors/reviews");
      const r = list.find((x) => x.id === reviewId);
      if (!r) throw new Error("Review not found");
      return r;
    },
    enabled: !!reviewId,
  });
  const respond = useRespondReview(reviewId);

  useEffect(() => {
    const u = getUser();
    if (!u) router.replace("/login");
    else setUser(u);
  }, [router]);

  async function handleRespond(e: React.FormEvent) {
    e.preventDefault();
    try {
      await respond.mutateAsync({ status, response_message: responseMessage || undefined });
      router.push("/advisor");
    } catch {
      // error
    }
  }

  if (!user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (isLoading || !review) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading review…</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/advisor" className="hover:underline">Review queue</Link>
        <span>/</span>
        <span>Review {reviewId.slice(0, 8)}</span>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Review request</CardTitle>
          <p className="text-sm text-muted-foreground">
            Project: {review.project_id} · From: {review.requester_name} · Status: {review.status}
          </p>
          {review.message && <p className="text-sm">{review.message}</p>}
        </CardHeader>
        <CardContent>
          <form onSubmit={handleRespond} className="space-y-4">
            <div className="space-y-2">
              <Label>Response status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="changes_requested">Changes requested</SelectItem>
                  <SelectItem value="in_progress">In progress</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="response">Response message (optional)</Label>
              <Input
                id="response"
                value={responseMessage}
                onChange={(e) => setResponseMessage(e.target.value)}
                placeholder="Feedback to the requester"
              />
            </div>
            <Button type="submit" disabled={respond.isPending}>
              {respond.isPending ? "Submitting…" : "Submit response"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUser } from "@/lib/auth";
import { useAdvisorReviews } from "@/hooks/use-reviews";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdvisorPage() {
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: reviews, isLoading } = useAdvisorReviews("pending");

  useEffect(() => {
    setUser(getUser());
  }, []);

  return (
    <div className="p-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold">Review queue</h1>
        <p className="text-muted-foreground">
          {user ? "Reviews assigned to you (pending)" : "Log in to see your review queue."}
        </p>
      </header>
      <Card>
        <CardHeader><CardTitle>Pending reviews</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading…</p>
          ) : !reviews?.length ? (
            <p className="text-muted-foreground">No pending reviews.</p>
          ) : (
            <ul className="space-y-2">
              {reviews.map((r) => (
                <li key={r.id}>
                  <Link
                    href={`/advisor/reviews/${r.id}`}
                    className="block rounded border p-3 hover:bg-muted/50"
                  >
                    <span className="font-medium">Project {r.project_id}</span>
                    <span className="ml-2 text-sm text-muted-foreground">
                      from {r.requester_name} — {r.status}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

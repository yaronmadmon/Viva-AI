"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getUser } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const user = getUser();
    if (user) {
      const role = (user.role || "student").toLowerCase();
      if (role === "advisor") router.replace("/advisor");
      else if (role === "examiner") router.replace("/examiner");
      else router.replace("/student");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">Redirecting…</p>
    </div>
  );
}

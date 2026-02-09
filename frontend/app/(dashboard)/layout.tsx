"use client";

import { useEffect, useState } from "react";
import { DashboardSidebar } from "@/components/dashboard-sidebar";
import { SkipToMain } from "@/components/skip-to-main";
import { CommandPalette } from "@/components/command-palette";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Login optional for now: no redirect when unauthenticated

  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <SkipToMain />
      <CommandPalette />
      <DashboardSidebar />
      <main id="main-content" className="flex-1 overflow-auto" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}

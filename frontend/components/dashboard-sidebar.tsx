"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout, getUser } from "@/lib/auth";
import type { UserResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { TeachingAvatar } from "@/components/teaching-avatar";
import { cn } from "@/lib/utils";

function NavLinks({ role, onNavigate }: { role: string; onNavigate?: () => void }) {
  const pathname = usePathname();
  const links: { href: string; label: string }[] = [];
  if (role === "student" || role === "admin") {
    links.push({ href: "/student", label: "Dashboard" });
  }
  if (role === "advisor" || role === "admin") {
    links.push({ href: "/advisor", label: "Review queue" });
    links.push({ href: "/advisor/projects", label: "Projects" });
  }
  if (role === "examiner" || role === "admin") {
    links.push({ href: "/examiner", label: "Projects" });
  }
  if (links.length === 0) links.push({ href: "/student", label: "Dashboard" });

  return (
    <nav className="flex flex-col gap-1">
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          onClick={onNavigate}
          className={cn(
            "rounded-md px-3 py-2 text-sm font-medium transition-colors",
            pathname === l.href || pathname?.startsWith(l.href + "/")
              ? "bg-muted text-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}

export function DashboardSidebar() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const pathname = usePathname();
  useEffect(() => {
    setUser(getUser());
  }, []);
  const roleLabel = (user?.role || "student").toLowerCase();
  const projectId = pathname?.match(/^\/student\/projects\/([^/]+)/)?.[1] ?? null;

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-56 border-r bg-muted/30 md:block">
        <div className="flex h-full flex-col gap-4 p-4">
          <Link href="/" className="font-semibold">
            Viva AI
          </Link>
          <NavLinks role={roleLabel} />
          {(roleLabel === "student" || roleLabel === "admin") && (
            <TeachingAvatar projectId={projectId} className="shrink-0" />
          )}
          <div className="mt-auto">
            {user ? (
              <>
                <p className="truncate px-3 text-xs text-muted-foreground">{user.full_name}</p>
                <p className="truncate px-3 text-xs text-muted-foreground capitalize">{roleLabel}</p>
                <Button variant="ghost" size="sm" className="mt-2 w-full justify-start" onClick={() => logout(true)}>
                  Log out
                </Button>
              </>
            ) : (
              <Link
                href="/login"
                className="inline-flex h-9 w-full items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground"
              >
                Log in
              </Link>
            )}
          </div>
        </div>
      </aside>
      {/* Mobile: hamburger + sheet */}
      <div className="flex items-center gap-2 border-b px-4 py-2 md:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Open menu">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-56" aria-describedby={undefined}>
            <SheetTitle className="sr-only">Navigation menu</SheetTitle>
            <div className="flex flex-col gap-4 pt-4">
              <span className="font-semibold">Viva AI</span>
              <NavLinks role={roleLabel} onNavigate={() => {}} />
              {(roleLabel === "student" || roleLabel === "admin") && (
                <TeachingAvatar projectId={projectId} className="shrink-0" />
              )}
              <div className="mt-auto">
                {user ? (
                  <>
                    <p className="text-sm text-muted-foreground">{user.full_name}</p>
                    <Button variant="outline" size="sm" className="mt-2 w-full" onClick={() => logout(true)}>
                      Log out
                    </Button>
                  </>
                ) : (
                  <Link
                    href="/login"
                    className="inline-flex h-9 w-full items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground"
                  >
                    Log in
                  </Link>
                )}
              </div>
            </div>
          </SheetContent>
        </Sheet>
        <span className="font-semibold">Viva AI</span>
      </div>
    </>
  );
}

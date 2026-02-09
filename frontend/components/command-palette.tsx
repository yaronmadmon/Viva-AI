"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useProjects } from "@/hooks/use-projects";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const user = typeof window !== "undefined" ? getUser() : null;
  const { data: projects } = useProjects();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const filtered =
    projects?.filter(
      (p) =>
        p.title.toLowerCase().includes(query.toLowerCase()) ||
        p.id.toLowerCase().includes(query.toLowerCase())
    ) ?? [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>Quick navigation</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Search projects..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="mt-2"
          aria-label="Search projects"
        />
        <div className="mt-2 max-h-60 overflow-auto">
          {user?.role?.toLowerCase() === "student" && (
            <button
              type="button"
              className="block w-full rounded px-2 py-2 text-left text-sm hover:bg-muted"
              onClick={() => {
                router.push("/student");
                setOpen(false);
              }}
            >
              Dashboard (Student)
            </button>
          )}
          {filtered.slice(0, 10).map((p) => (
            <button
              key={p.id}
              type="button"
              className="block w-full rounded px-2 py-2 text-left text-sm hover:bg-muted"
              onClick={() => {
                if (user?.role?.toLowerCase() === "student" || user?.role?.toLowerCase() === "admin") {
                  router.push(`/student/projects/${p.id}`);
                } else if (user?.role?.toLowerCase() === "advisor") {
                  router.push(`/advisor/projects/${p.id}/submission-units`);
                } else {
                  router.push(`/examiner/projects/${p.id}`);
                }
                setOpen(false);
              }}
            >
              {p.title}
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

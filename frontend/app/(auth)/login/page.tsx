"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, APIError, BASE_URL } from "@/lib/api";
import { login } from "@/lib/auth";
import type { TokenResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  useEffect(() => {
    const base = BASE_URL.replace(/\/api\/v1\/?$/, "");
    fetch(`${base}/health`)
      .then((r) => r.ok)
      .then(setBackendOk)
      .catch(() => setBackendOk(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api<TokenResponse>("auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      if (!data?.user || !data?.access_token) {
        setError("Invalid response from server. Try again.");
        return;
      }
      login(data);
      router.push("/");
      router.refresh();
    } catch (err) {
      if (err instanceof APIError) {
        const msg = err.detail || "Request failed";
        setError(msg);
      } else if (err instanceof TypeError && (err.message === "Failed to fetch" || (err.message && err.message.includes("network")))) {
        setError("Cannot reach the server. Start the backend (see below), then try again.");
        setBackendOk(false);
      } else {
        setError(err instanceof Error ? err.message : "Login failed");
      }
    } finally {
      setLoading(false);
    }
  }

  async function recheckBackend() {
    setError(null);
    const base = BASE_URL.replace(/\/api\/v1\/?$/, "");
    try {
      const ok = await fetch(`${base}/health`).then((r) => r.ok);
      setBackendOk(ok);
      if (ok) setError(null);
    } catch {
      setBackendOk(false);
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6 rounded-lg border bg-card p-6 shadow-sm">
      <h1 className="text-xl font-semibold">Sign in to Viva AI</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        {backendOk === false && (
          <div className="space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200" role="alert">
            <p className="font-medium">Backend not reachable</p>
            <p className="text-xs">From the project root run:</p>
            <code className="block break-all rounded bg-amber-100 px-2 py-1 text-xs dark:bg-amber-900/50">
              python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
            </code>
            <p className="text-xs">Then click below to retry.</p>
            <Button type="button" variant="outline" size="sm" onClick={recheckBackend} className="mt-1">
              Check connection again
            </Button>
          </div>
        )}
        {error && (
          <div className="space-y-1" role="alert">
            <p className="text-sm text-destructive">{error}</p>
            {(error === "Invalid email or password" || error.toLowerCase().includes("invalid")) && (
              <p className="text-xs text-muted-foreground">
                Make sure you’ve <Link href="/register" className="underline">registered</Link> and are using the correct password. Email is case-insensitive.
              </p>
            )}
          </div>
        )}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-primary underline">
          Register
        </Link>
      </p>
      <p className="text-center text-xs text-muted-foreground">
        Backend must be running at <code className="rounded bg-muted px-1">http://localhost:8000</code>. Can&apos;t login? Ensure you&apos;ve <Link href="/register" className="underline">registered</Link> and the backend is started.
      </p>
    </div>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getUser } from "@/lib/auth";
import { useProject } from "@/hooks/use-projects";
import { useArtifact, useUpdateArtifact } from "@/hooks/use-artifacts";
import {
  useMasteryCapabilities,
  useGenerateAISuggestion,
  useAcceptAISuggestion,
  useRejectAISuggestion,
} from "@/hooks/use-mastery";
import { saveDraft, getDraft, clearDraft } from "@/lib/offline";
import type { AISuggestionGenerateResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SUGGESTION_TYPES = [
  { value: "outline", label: "Outline" },
  { value: "paragraph_draft", label: "Paragraph draft" },
  { value: "source_summary", label: "Source summary" },
  { value: "gap_analysis", label: "Gap analysis" },
  { value: "claim_refinement", label: "Claim refinement" },
  { value: "method_template", label: "Method template" },
  { value: "defense_question", label: "Defense question" },
] as const;

export default function EditArtifactPage() {
  const params = useParams();
  const projectId = params?.id as string;
  const artifactId = params?.aid as string;
  const [user, setUser] = useState<ReturnType<typeof getUser>>(null);
  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: artifact, isLoading: artifactLoading } = useArtifact(artifactId);
  const updateArtifact = useUpdateArtifact(artifactId);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "synced" | "error">("idle");
  const [hasDraft, setHasDraft] = useState(false);
  const [suggestionType, setSuggestionType] = useState<string>(SUGGESTION_TYPES[0].value);
  const [suggestion, setSuggestion] = useState<AISuggestionGenerateResponse | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const { data: capabilities } = useMasteryCapabilities(projectId);
  const generateSuggestion = useGenerateAISuggestion(projectId);
  const acceptSuggestion = useAcceptAISuggestion(projectId);
  const rejectSuggestion = useRejectAISuggestion(projectId);

  const loadDraft = useCallback(async () => {
    const draft = await getDraft(artifactId);
    if (draft) {
      setTitle(draft.title ?? "");
      setContent(draft.content);
      setHasDraft(true);
      return true;
    }
    return false;
  }, [artifactId]);

  useEffect(() => {
    setUser(getUser());
  }, []);

  useEffect(() => {
    if (!artifact) return;
    loadDraft().then((hadDraft) => {
      if (!hadDraft) {
        setTitle(artifact.title ?? "");
        setContent(artifact.content ?? "");
      }
    });
  }, [artifact, loadDraft]);

  async function handleSaveDraft() {
    setSaveStatus("saving");
    await saveDraft(artifactId, projectId, { title, content });
    setHasDraft(true);
    setSaveStatus("saved");
    setTimeout(() => setSaveStatus("idle"), 2000);
  }

  async function handleCommit() {
    setSaveStatus("saving");
    try {
      await updateArtifact.mutateAsync({ title: title || undefined, content });
      await clearDraft(artifactId);
      setHasDraft(false);
      setSaveStatus("synced");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  }

  async function handleGetSuggestion() {
    setAiError(null);
    setSuggestion(null);
    try {
      const res = await generateSuggestion.mutateAsync({
        artifact_id: artifactId,
        suggestion_type: suggestionType,
      });
      setSuggestion(res);
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string };
      if (err?.status === 403) {
        setAiError("This suggestion type is not unlocked. Complete checkpoints in Mastery to unlock.");
      } else {
        setAiError(err?.message ?? "Failed to generate suggestion.");
      }
    }
  }

  async function handleAcceptSuggestion(mergeIntoContent: boolean) {
    if (!suggestion) return;
    try {
      await acceptSuggestion.mutateAsync({
        suggestion_id: suggestion.suggestion_id,
        artifact_id: artifactId,
        suggestion_type: suggestion.suggestion_type,
      });
      if (mergeIntoContent) {
        setContent((prev) => (prev ? prev + "\n\n" + suggestion.content : suggestion.content));
      }
      setSuggestion(null);
      setAiError(null);
    } catch {
      setAiError("Failed to accept suggestion.");
    }
  }

  async function handleRejectSuggestion() {
    if (!suggestion) return;
    try {
      await rejectSuggestion.mutateAsync({
        suggestion_id: suggestion.suggestion_id,
        artifact_id: artifactId,
        suggestion_type: suggestion.suggestion_type,
      });
      setSuggestion(null);
      setAiError(null);
    } catch {
      setAiError("Failed to reject suggestion.");
    }
  }

  if (!user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (projectLoading || !project) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading project…</p>
      </div>
    );
  }

  if (artifactLoading || !artifact) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading artifact…</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link href="/student" className="hover:underline">
              Dashboard
            </Link>
            <span>/</span>
            <Link href={`/student/projects/${projectId}`} className="hover:underline">
              {project.title}
            </Link>
            <span>/</span>
            <span>{artifact.title || "(untitled)"}</span>
          </div>
          <h1 className="mt-1 text-xl font-semibold">
            Edit artifact · {artifact.artifact_type}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {saveStatus === "saving" && <span className="text-sm text-muted-foreground">Saving…</span>}
          {saveStatus === "saved" && <span className="text-sm text-muted-foreground">Saved (draft)</span>}
          {saveStatus === "synced" && <span className="text-sm text-green-600">Synced</span>}
          {saveStatus === "error" && <span className="text-sm text-destructive">Failed to sync</span>}
          <Button variant="outline" onClick={handleSaveDraft} disabled={saveStatus === "saving"}>
            Save draft
          </Button>
          <Button onClick={handleCommit} disabled={saveStatus === "saving"}>
            Commit
          </Button>
        </div>
      </header>

      <div className="max-w-2xl space-y-4">
        <div className="space-y-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="content">Content</Label>
          <textarea
            id="content"
            className="min-h-[300px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Content..."
          />
        </div>
        {hasDraft && (
          <p className="text-sm text-muted-foreground">
            You have unsaved draft changes. Save draft to keep locally, or Commit to push to server.
          </p>
        )}

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>AI suggestions</CardTitle>
            <p className="text-sm text-muted-foreground">
              Generate suggestions for this artifact. Unlock more types by completing checkpoints in Mastery.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Select value={suggestionType} onValueChange={setSuggestionType}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SUGGESTION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                onClick={handleGetSuggestion}
                disabled={generateSuggestion.isPending}
                variant="secondary"
              >
                {generateSuggestion.isPending ? "Generating…" : "Get AI suggestion"}
              </Button>
            </div>
            {aiError && (
              <p className="text-sm text-destructive">{aiError}</p>
            )}
            {suggestion && (
              <div className="space-y-2 rounded-lg border bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">
                  {suggestion.suggestion_type} · {suggestion.word_count} words
                  {suggestion.model_used && suggestion.model_used !== "stub" && ` · ${suggestion.model_used}`}
                </p>
                <div className="max-h-48 overflow-auto whitespace-pre-wrap text-sm">
                  {suggestion.content}
                </div>
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    onClick={() => handleAcceptSuggestion(true)}
                    disabled={acceptSuggestion.isPending}
                  >
                    Accept and add to content
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAcceptSuggestion(false)}
                    disabled={acceptSuggestion.isPending}
                  >
                    Accept (record only)
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRejectSuggestion()}
                    disabled={rejectSuggestion.isPending}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

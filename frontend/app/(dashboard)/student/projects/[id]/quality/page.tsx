"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQualityReport } from "@/hooks/use-quality-report";
import { useProject } from "@/hooks/use-projects";
import type {
  ClaimAuditResponse,
  MethodologyStressResponse,
  ContributionCheckResponse,
  LiteratureTensionResponse,
} from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/* ------------------------------------------------------------------ */
/*  Small helper components                                           */
/* ------------------------------------------------------------------ */

function Badge({
  children,
  variant = "default",
}: {
  children: React.ReactNode;
  variant?: "pass" | "fail" | "warn" | "default";
}) {
  const colors = {
    pass: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    fail: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    warn: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    default:
      "bg-muted text-muted-foreground",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colors[variant]}`}
    >
      {children}
    </span>
  );
}

function ScoreRing({
  score,
  size = 96,
  passed,
}: {
  score: number;
  size?: number;
  passed: boolean;
}) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = passed
    ? "stroke-emerald-500"
    : score >= 50
    ? "stroke-amber-500"
    : "stroke-red-500";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={10}
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={10}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${color} transition-all duration-700`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold">{Math.round(score)}</span>
        <span className="text-[10px] text-muted-foreground">/100</span>
      </div>
    </div>
  );
}

function Check({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="text-emerald-600 dark:text-emerald-400 font-bold">&#10003;</span>
  ) : (
    <span className="text-red-500 font-bold">&#10007;</span>
  );
}

function ProgressBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color =
    pct >= 70
      ? "bg-emerald-500"
      : pct >= 40
      ? "bg-amber-500"
      : "bg-red-500";
  return (
    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Section cards                                                     */
/* ------------------------------------------------------------------ */

function ClaimDisciplineCard({
  data,
}: {
  data: ClaimAuditResponse;
}) {
  const total = data.total_sentences || 1;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Claim Discipline</CardTitle>
            <CardDescription>
              Sentence-level classification &amp; hedging analysis
            </CardDescription>
          </div>
          <Badge variant={data.passed ? "pass" : "fail"}>
            {data.passed ? "PASS" : "NEEDS WORK"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Distribution bar */}
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">
            Sentence distribution ({data.total_sentences} total)
          </p>
          <div className="flex h-5 w-full overflow-hidden rounded-full">
            <div
              className="bg-blue-500 transition-all"
              style={{ width: `${(data.descriptive_count / total) * 100}%` }}
              title={`Descriptive: ${data.descriptive_count}`}
            />
            <div
              className="bg-amber-500 transition-all"
              style={{ width: `${(data.inferential_count / total) * 100}%` }}
              title={`Inferential: ${data.inferential_count}`}
            />
            <div
              className="bg-purple-500 transition-all"
              style={{ width: `${(data.speculative_count / total) * 100}%` }}
              title={`Speculative: ${data.speculative_count}`}
            />
          </div>
          <div className="mt-1.5 flex gap-4 text-xs">
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm bg-blue-500" /> Descriptive:{" "}
              {data.descriptive_count}
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm bg-amber-500" /> Inferential:{" "}
              {data.inferential_count}
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm bg-purple-500" /> Speculative:{" "}
              {data.speculative_count}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold text-red-500">{data.overreach_count}</p>
            <p className="text-xs text-muted-foreground">Overreach</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold text-amber-500">
              {data.unhedged_inferential_count}
            </p>
            <p className="text-xs text-muted-foreground">Unhedged</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{data.certainty_score}</p>
            <p className="text-xs text-muted-foreground">Certainty</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{data.total_sentences}</p>
            <p className="text-xs text-muted-foreground">Sentences</p>
          </div>
        </div>

        {/* Flags */}
        {data.flags.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">
              Flagged sentences ({data.flags.length})
            </p>
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {data.flags.map((f, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/30"
                >
                  <p className="text-xs font-medium text-amber-800 dark:text-amber-300">
                    [{f.severity}] {f.issue}
                  </p>
                  <p className="mt-1 text-xs italic text-muted-foreground line-clamp-2">
                    &ldquo;{f.sentence}&rdquo;
                  </p>
                  {f.suggestion && (
                    <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-400">
                      Fix: {f.suggestion}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MethodologyCard({
  data,
}: {
  data: MethodologyStressResponse;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Methodology Stress Test</CardTitle>
            <CardDescription>
              Is the methodology a defensive argument?
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">
              {Math.round(data.defensibility_score)}
            </span>
            <span className="text-xs text-muted-foreground">/100</span>
            <Badge variant={data.passed ? "pass" : "fail"}>
              {data.passed ? "PASS" : "NEEDS WORK"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <ProgressBar value={data.defensibility_score} />

        {/* Checklist */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="flex items-center gap-2 rounded-lg border p-2.5">
            <Check ok={data.has_rejected_alternatives} />
            <span className="text-xs">Rejected alternatives</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border p-2.5">
            <Check ok={data.has_failure_conditions} />
            <span className="text-xs">Failure conditions</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border p-2.5">
            <Check ok={data.has_boundary_conditions} />
            <span className="text-xs">Boundary conditions</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border p-2.5">
            <Check ok={data.has_justification} />
            <span className="text-xs">Design justification</span>
          </div>
        </div>

        {/* Examiner questions */}
        {data.examiner_questions.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">
              Examiner questions ({data.examiner_questions.length})
            </p>
            <div className="space-y-2">
              {data.examiner_questions.map((q, i) => (
                <div
                  key={i}
                  className="rounded-lg border p-3"
                >
                  <p className="text-sm">{q.question}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Category: {q.category}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Flags */}
        {data.flags.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">Issues</p>
            {data.flags.map((f, i) => (
              <div
                key={i}
                className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/30"
              >
                <p className="text-xs font-medium text-amber-800 dark:text-amber-300">
                  [{f.severity}] {f.issue}
                </p>
                {f.suggestion && (
                  <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-400">
                    Fix: {f.suggestion}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ContributionCard({
  data,
}: {
  data: ContributionCheckResponse;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Contribution Validator</CardTitle>
            <CardDescription>
              Is the contribution surgically precise?
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">
              {Math.round(data.precision_score)}
            </span>
            <span className="text-xs text-muted-foreground">/100</span>
            <Badge variant={data.passed ? "pass" : "fail"}>
              {data.passed ? "PASS" : "NEEDS WORK"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ProgressBar value={data.precision_score} />

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{data.claim_count}</p>
            <p className="text-xs text-muted-foreground">Core claims</p>
          </div>
          <div className="flex items-center gap-2 rounded-lg border p-3">
            <Check ok={data.has_before_after} />
            <span className="text-xs">Before / After framing</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border p-3">
            <Check ok={data.has_falsifiability} />
            <span className="text-xs">Falsifiability</span>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold text-red-500">
              {data.broad_claim_count}
            </p>
            <p className="text-xs text-muted-foreground">Broad claims</p>
          </div>
        </div>

        {data.flags.length > 0 && (
          <div className="space-y-2">
            {data.flags.map((f, i) => (
              <div
                key={i}
                className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/30"
              >
                <p className="text-xs">{f.issue}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function LiteratureTensionCard({
  data,
}: {
  data: LiteratureTensionResponse;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Literature Tension</CardTitle>
            <CardDescription>
              Named disagreements &amp; conflict mapping
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">
              {Math.round(data.tension_score)}
            </span>
            <span className="text-xs text-muted-foreground">/100</span>
            <Badge variant={data.passed ? "pass" : "fail"}>
              {data.passed ? "PASS" : "NEEDS WORK"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ProgressBar value={data.tension_score} />

        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{data.named_disagreement_count}</p>
            <p className="text-xs text-muted-foreground">Named disagreements</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold text-amber-500">
              {data.vague_attribution_count}
            </p>
            <p className="text-xs text-muted-foreground">Vague attributions</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-2xl font-bold">{data.total_paragraphs}</p>
            <p className="text-xs text-muted-foreground">Paragraphs</p>
          </div>
        </div>

        {/* Named disagreements */}
        {data.named_disagreements.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">Disagreements found</p>
            <div className="space-y-1.5">
              {data.named_disagreements.map((nd, i) => (
                <div key={i} className="flex items-center gap-2 rounded-lg border p-2.5">
                  <span className="text-sm font-medium">{nd.author_a}</span>
                  <span className="text-xs text-muted-foreground">vs</span>
                  <span className="text-sm font-medium">{nd.author_b}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Flags */}
        {data.flags.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium">Issues</p>
            <div className="space-y-2">
              {data.flags.map((f, i) => (
                <div
                  key={i}
                  className={`rounded-lg border p-3 ${
                    f.severity === "error"
                      ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30"
                      : "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30"
                  }`}
                >
                  <p
                    className={`text-xs font-medium ${
                      f.severity === "error"
                        ? "text-red-800 dark:text-red-300"
                        : "text-amber-800 dark:text-amber-300"
                    }`}
                  >
                    [{f.severity}] {f.issue}
                  </p>
                  {f.suggestion && (
                    <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-400">
                      Fix: {f.suggestion}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */

export default function QualityReportPage() {
  const params = useParams();
  const projectId = params?.id as string | undefined;
  const { data: project } = useProject(projectId ?? null);
  const { data: report, isLoading, error } = useQualityReport(projectId ?? null);

  return (
    <div className="p-6">
      {/* Breadcrumb */}
      <header className="mb-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="/student" className="hover:underline">
            Dashboard
          </Link>
          <span>/</span>
          {projectId && (
            <>
              <Link
                href={`/student/projects/${projectId}`}
                className="hover:underline"
              >
                {project?.title ?? "Project"}
              </Link>
              <span>/</span>
            </>
          )}
          <span>Quality Report</span>
        </div>
        <h1 className="mt-1 text-xl font-semibold">
          Harvard-Level Quality Report
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Automated audit of claim discipline, methodology defensibility,
          contribution precision, and literature tension.
        </p>
      </header>

      {/* Loading */}
      {isLoading && (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">
                Running quality engines... this may take a moment.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {error && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <CardContent className="py-6">
            <p className="text-sm text-red-700 dark:text-red-300">
              Failed to load quality report:{" "}
              {(error as Error).message || "Unknown error"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Report */}
      {report && (
        <div className="space-y-6">
          {/* Overall score card */}
          <Card
            className={
              report.passed
                ? "border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-950/20"
                : "border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20"
            }
          >
            <CardContent className="flex flex-col items-center gap-4 py-8 sm:flex-row sm:justify-between">
              <div className="flex items-center gap-6">
                <ScoreRing
                  score={report.overall_score}
                  passed={report.passed}
                />
                <div>
                  <h2 className="text-lg font-semibold">
                    Overall Quality Score
                  </h2>
                  <Badge variant={report.passed ? "pass" : "warn"}>
                    {report.passed ? "PASSED" : "NEEDS IMPROVEMENT"}
                  </Badge>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    {report.summary}
                  </p>
                </div>
              </div>

              {/* Sub-score mini cards */}
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg border bg-background px-4 py-2">
                  <p className="text-lg font-bold">
                    {report.claim_audit
                      ? Math.round(100 - report.claim_audit.certainty_score)
                      : "—"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Claims</p>
                </div>
                <div className="rounded-lg border bg-background px-4 py-2">
                  <p className="text-lg font-bold">
                    {report.methodology_stress
                      ? Math.round(report.methodology_stress.defensibility_score)
                      : "—"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Method</p>
                </div>
                <div className="rounded-lg border bg-background px-4 py-2">
                  <p className="text-lg font-bold">
                    {report.contribution_check
                      ? Math.round(report.contribution_check.precision_score)
                      : "—"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    Contribution
                  </p>
                </div>
                <div className="rounded-lg border bg-background px-4 py-2">
                  <p className="text-lg font-bold">
                    {report.literature_tension
                      ? Math.round(report.literature_tension.tension_score)
                      : "—"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Tension</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Individual engine cards */}
          {report.claim_audit && (
            <ClaimDisciplineCard data={report.claim_audit} />
          )}
          {report.methodology_stress && (
            <MethodologyCard data={report.methodology_stress} />
          )}
          {report.contribution_check && (
            <ContributionCard data={report.contribution_check} />
          )}
          {report.literature_tension && (
            <LiteratureTensionCard data={report.literature_tension} />
          )}
        </div>
      )}
    </div>
  );
}

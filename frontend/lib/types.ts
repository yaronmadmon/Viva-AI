/**
 * Frontend types mirroring backend DTOs (src/schemas).
 */

export type UserRole = "student" | "advisor" | "examiner" | "admin";

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  verified_at: string | null;
  mastery_tier: number;
  ai_disclosure_level: number;
  total_words_written: number;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface ProjectResponse {
  id: string;
  title: string;
  description: string | null;
  discipline_type: string;
  status: string;
  owner_id: string;
  owner_name: string | null;
  integrity_score: number;
  export_blocked: boolean;
  artifact_count: number;
  generation_pending?: boolean;
  created_at: string;
  updated_at: string;
}

export interface GenerationStatusSection {
  title: string;
  word_count: number;
  is_generated: boolean;
}

export interface GenerationStatusResponse {
  project_id: string;
  total_words: number;
  total_sections: number;
  generated_sections: number;
  all_generated: boolean;
  sections: GenerationStatusSection[];
}

export interface ProjectListResponse {
  id: string;
  title: string;
  description: string | null;
  discipline_type: string;
  status: string;
  owner_id: string;
  owner_name: string | null;
  integrity_score: number;
  is_owner: boolean;
  permission_level: string;
  artifact_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  artifact_type: string;
  title: string | null;
  content: string;
}

export interface ProjectDocumentResponse {
  project_id: string;
  artifacts: DocumentChunk[];
}

export interface ArtifactResponse {
  id: string;
  project_id: string;
  artifact_type: string;
  title: string | null;
  content: string;
  content_hash: string;
  version: number;
  parent_id: string | null;
  position: number;
  contribution_category: string;
  ai_modification_ratio: number;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  children_count?: number;
  outgoing_links_count?: number;
  incoming_links_count?: number;
  comment_count?: number;
}

export interface ArtifactLinkResponse {
  id: string;
  source_artifact_id: string;
  target_artifact_id: string;
  link_type: string;
  strength: number;
  annotation: string | null;
  created_by: string;
  created_at: string;
  target_title?: string | null;
  target_type?: string | null;
  source_title?: string | null;
  source_type?: string | null;
}

export interface ArtifactDetailResponse extends ArtifactResponse {
  children: ArtifactResponse[];
  outgoing_links: ArtifactLinkResponse[];
  incoming_links: ArtifactLinkResponse[];
}

export interface ArtifactTreeNode {
  id: string;
  artifact_type: string;
  title: string | null;
  position: number;
  version: number;
  children: ArtifactTreeNode[];
}

export interface ArtifactTreeResponse {
  project_id: string;
  root_artifacts: ArtifactTreeNode[];
  total_count: number;
}

export interface SubmissionUnitResponse {
  id: string;
  project_id: string;
  title: string;
  artifact_ids: string[] | null;
  state: string;
  state_changed_at: string | null;
  state_changed_by: string | null;
  current_review_request_id: string | null;
  last_approved_at: string | null;
  approval_version: number | null;
  created_at: string;
  updated_at: string;
}

export interface CheckpointAttemptSummary {
  checkpoint_type: string;
  passed: boolean;
  score: number;
  completed_at: string;
}

export interface MasteryProgressResponse {
  current_tier: number;
  ai_level: number;
  total_words_written: number;
  next_checkpoint: string | null;
  attempts: CheckpointAttemptSummary[];
}

export interface ReviewRequestResponse {
  id: string;
  project_id: string;
  artifact_id: string | null;
  requested_by: string;
  requester_name: string | null;
  reviewer_id: string;
  reviewer_name: string | null;
  status: string;
  message: string | null;
  response_message: string | null;
  responded_at: string | null;
  created_at: string;
}

export interface APIErrorDetail {
  detail: string | { message?: string; errors?: Array<{ field: string; message: string }> };
}

// Submission unit state transitions (student: draft/revisions_required -> ready_for_review)
export const SUBMISSION_UNIT_STUDENT_NEXT = ["ready_for_review"] as const;

// Mastery
export interface CheckpointQuestionSchema {
  id: string;
  question_type: string;
  text: string;
  options?: string[] | null;
  topic: string;
  difficulty: number;
  grading_rubric?: string | null;
}

export interface CheckpointStartResponse {
  tier: number;
  checkpoint_type: string;
  questions: CheckpointQuestionSchema[];
  required_count: number;
  pass_threshold_description: string;
}

export interface QuestionResultResponse {
  question_id: string;
  correct: boolean;
  user_answer: string;
  word_count?: number | null;
}

export interface CheckpointResultResponse {
  checkpoint_type: string;
  total_questions: number;
  correct_answers: number;
  score_percentage: number;
  passed: boolean;
  question_results: QuestionResultResponse[];
  attempt_number: number;
  tier_unlocked?: number | null;
  ai_level_unlocked?: number | null;
}

export interface CapabilityItem {
  capability: string;
  description?: string | null;
}

export interface CapabilitiesResponse {
  ai_level: number;
  level_description: string;
  capabilities: CapabilityItem[];
  next_level_requirements: string;
}

export interface AISuggestionGenerateResponse {
  suggestion_id: string;
  suggestion_type: string;
  content: string;
  confidence: number;
  watermark_hash: string;
  word_count: number;
  truncated: boolean;
  requires_checkbox: boolean;
  min_modification_required?: number | null;
  generated_at: string;
  model_used?: string;
}

// Guidance, certification, curriculum, defense
export interface GuidanceRule {
  id: string;
  message: string;
  priority: number;
  cta?: string;
  cta_path?: string | null;
}

export interface GuidanceNextResponse {
  project_id: string;
  rules: GuidanceRule[];
}

export interface CertificationResponse {
  project_id: string;
  ready: boolean;
  components: { mastery?: boolean; integrity?: boolean; defense?: boolean };
}

export interface CurriculumConceptsResponse {
  project_id: string;
  discipline: string;
  concepts: unknown[];
}

export interface DefensePracticeResponse {
  project_id: string;
  mode: string;
  questions: { id: string; text: string; tier?: number }[];
}

// Avatar chat
export interface AvatarChatResponse {
  reply: string;
  model_used: string;
  requires_contract: boolean;
  teaching_mode: string;
}

export interface AvatarHistoryMessage {
  role: string;
  text: string;
  teaching_mode: string | null;
  created_at: string;
}

export interface AvatarHistoryResponse {
  project_id: string;
  messages: AvatarHistoryMessage[];
  total_count: number;
}

// Quality report (Harvard-level engines)
export interface ClaimFlag {
  sentence: string;
  level: string;
  issue: string;
  severity: string;
  suggestion: string | null;
  line_hint?: number;
}

export interface ClaimAuditResponse {
  section_title: string;
  total_sentences: number;
  descriptive_count: number;
  inferential_count: number;
  speculative_count: number;
  overreach_count: number;
  unhedged_inferential_count: number;
  certainty_score: number;
  passed: boolean;
  flags: ClaimFlag[];
}

export interface ExaminerQuestion {
  question: string;
  category: string;
  expected_elements?: string[];
}

export interface MethodologyFlag {
  issue: string;
  severity: string;
  category: string;
  suggestion?: string;
}

export interface MethodologyStressResponse {
  has_rejected_alternatives: boolean;
  has_failure_conditions: boolean;
  has_boundary_conditions: boolean;
  has_justification: boolean;
  procedural_ratio: number;
  defensibility_score: number;
  passed: boolean;
  examiner_questions: ExaminerQuestion[];
  flags: MethodologyFlag[];
}

export interface ContributionCheckResponse {
  claim_count: number;
  has_before_after: boolean;
  has_falsifiability: boolean;
  broad_claim_count: number;
  precision_score: number;
  passed: boolean;
  flags: { issue: string; severity: string; suggestion?: string }[];
}

export interface NamedDisagreement {
  author_a: string;
  author_b: string;
  context?: string;
}

export interface LiteratureTensionResponse {
  total_paragraphs: number;
  named_disagreement_count: number;
  vague_attribution_count: number;
  tension_style_count: number;
  synthesis_count: number;
  tension_score: number;
  passed: boolean;
  named_disagreements: NamedDisagreement[];
  flags: { issue: string; severity: string; suggestion?: string }[];
}

export interface PedagogicalAnnotation {
  paragraph_index: number;
  annotation_type: string;
  annotation: string;
  target_text?: string;
}

export interface PedagogicalAnnotationsResponse {
  section_title: string;
  annotation_count: number;
  annotations: PedagogicalAnnotation[];
}

export interface FullQualityReportResponse {
  project_id: string;
  sections_audited: number;
  overall_score: number;
  passed: boolean;
  summary: string;
  claim_audit: ClaimAuditResponse | null;
  methodology_stress: MethodologyStressResponse | null;
  contribution_check: ContributionCheckResponse | null;
  literature_tension: LiteratureTensionResponse | null;
}

// Integrity & export
export interface IntegrityReportItem {
  category: string;
  status: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface IntegrityReport {
  project_id: string;
  project_title: string;
  generated_at: string;
  overall_score: number;
  export_allowed: boolean;
  total_artifacts: number;
  total_words: number;
  total_sources: number;
  total_links: number;
  ai_suggestions_accepted: number;
  ai_suggestions_rejected: number;
  avg_modification_ratio: number;
  primarily_human_count: number;
  human_guided_count: number;
  ai_reviewed_count: number;
  unmodified_ai_count: number;
  items: IntegrityReportItem[];
  blocking_issues: string[];
}

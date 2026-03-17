/** TypeScript types mirroring FastAPI Pydantic models. */

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'pending_review' | 'reviewed'
export type ExtractionMode = 'local_only' | 'cloud' | 'auto'

export interface SchemaField {
  label: string
  type: 'text' | 'number' | 'date' | 'boolean'
  occurrence?: 'required once' | 'optional once' | 'optional multiple'
  description?: string
}

export interface ExtractionResult {
  label: string
  value: string | number | boolean | null
  confidence: number
}

export interface CostResponse {
  input_tokens: number
  output_tokens: number
  estimated_cost_usd: number
}

export interface JobResponse {
  id: string
  status: JobStatus
  mode: string
  cloud_provider?: string | null
  created_at: string
  completed_at?: string | null
  result?: ExtractionResult[] | null
  confidence?: number | null
  cost?: CostResponse | null
  error?: string | null
}

export interface JobListResponse {
  jobs: JobResponse[]
  total: number
}

export interface SchemaResponse {
  id: string
  name: string
  fields: SchemaField[]
  created_at: string
  updated_at: string
}

export interface SchemaCreateRequest {
  name: string
  fields: SchemaField[]
}

// Pipeline types (Phase 2 additions)
export interface PipelineStep {
  provider: string
  model?: string
  fallback?: boolean
}

export interface PipelineResponse {
  id: string
  name: string
  description?: string | null
  config: string // YAML string
  created_at: string
  updated_at: string
}

export interface PipelineCreateRequest {
  name: string
  description?: string
  config: string
}

// Batch types
export type BatchStatus = 'pending' | 'processing' | 'completed' | 'partial' | 'failed'

export interface BatchResponse {
  id: string
  status: BatchStatus
  total_files: number
  processed_files: number
  failed_files: number
  created_at: string
  completed_at?: string | null
  job_ids?: string[]
}

export interface BatchListResponse {
  batches: BatchResponse[]
  total: number
}

// Webhook types
export type WebhookEvent =
  | 'job.completed'
  | 'job.failed'
  | 'batch.completed'
  | 'batch.failed'

export interface WebhookSubscription {
  id: string
  url: string
  events: WebhookEvent[]
  workspace_id: string
  active: boolean
  created_at: string
}

export interface WebhookDelivery {
  id: string
  webhook_id: string
  event: WebhookEvent
  status: 'success' | 'failed' | 'pending'
  response_status?: number | null
  attempt: number
  created_at: string
}

// API Key types
export interface ApiKeyResponse {
  id: string
  name: string
  key_prefix: string
  created_at: string
  last_used_at?: string | null
  active: boolean
}

export interface ApiKeyCreateResponse extends ApiKeyResponse {
  key: string // Only returned at creation time
}

// Workspace types
export interface WorkspaceResponse {
  id: string
  name: string
  slug: string
  created_at: string
}

// Schema suggest & template types
export interface SuggestedField {
  label: string
  type: 'text' | 'number' | 'date' | 'boolean'
  occurrence: string
  confidence: number
}

export interface SuggestSchemaResponse {
  fields: SuggestedField[]
  warning: string
  beta: boolean
}

export interface SchemaTemplate {
  id: string
  name: string
  description: string
  category: string
  fields: SchemaField[]
  languages: string[]
  is_curated: boolean
  usage_count: number
  version: string
  created_at: string
}

export interface TemplateListResponse {
  templates: SchemaTemplate[]
  total: number
}

// Review types
export type ReviewStatus = 'approved' | 'corrected'

export interface ReviewCorrection {
  field: string
  original: string | number | boolean | null
  corrected: string | number | boolean | null
}

export interface ReviewResponse {
  id: string
  job_id: string
  workspace_id: string
  status: ReviewStatus
  original_result: ExtractionResult[]
  corrected_result?: ExtractionResult[] | null
  corrections?: ReviewCorrection[] | null
  reviewer_id?: string | null
  review_time_ms?: number | null
  created_at: string
}

export interface ReviewListResponse {
  reviews: ReviewResponse[]
  total: number
}

export interface ReviewRequest {
  status: ReviewStatus
  corrected_result?: Record<string, unknown>[] | null
  reviewer_id?: string | null
  review_time_ms?: number | null
}

// Accuracy types
export interface FieldAccuracyDetail {
  correct: number
  total: number
  accuracy_pct: number
}

export interface AccuracyMetric {
  id?: string
  period_start: string
  period_end: string
  total_reviews: number
  approved_count: number
  corrected_count: number
  accuracy_pct: number
  field_accuracy: Record<string, FieldAccuracyDetail>
}

// Analytics types
export interface DailyUsageStat {
  date: string
  job_count: number
  success_count: number
  failed_count: number
  review_count: number
  avg_confidence: number | null
}

export interface DailyCostStat {
  date: string
  total_cost_usd: number
  total_input_tokens: number
  total_output_tokens: number
  provider_breakdown: Record<string, number>
}

export interface ProviderStat {
  provider: string
  job_count: number
  success_rate: number
  avg_confidence: number | null
  avg_latency_ms: number | null
  total_cost_usd: number
}

export interface AnalyticsOverview {
  total_jobs: number
  total_cost_usd: number
  avg_confidence: number | null
  active_schemas: number
  period: string
}

// Approval workflow types
export type PolicyType = 'chain' | 'quorum'
export type RoundType = 'review' | 'approve' | 'escalation'
export type RoundStatus = 'pending' | 'in_progress' | 'completed' | 'escalated'
export type AssignmentStatus = 'pending' | 'in_progress' | 'approved' | 'corrected' | 'rejected'

export interface ApprovalPolicy {
  id: string
  workspace_id: string
  name: string
  policy_type: PolicyType
  config: Record<string, unknown>
  deadline_hours?: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ReviewRound {
  id: string
  job_id: string
  round_number: number
  round_type: RoundType
  status: RoundStatus
  required_approvals: number
  deadline_at?: string | null
  created_at: string
  completed_at?: string | null
}

export interface ReviewAssignment {
  id: string
  user_id: string
  status: AssignmentStatus
  completed_at?: string | null
}

export interface ReviewStatusResponse {
  job_id: string
  policy_name: string
  policy_type: PolicyType
  current_round: number
  total_rounds?: number | null
  round_status: RoundStatus
  assignments: ReviewAssignment[]
  deadline_at?: string | null
}

export interface ReviewQueueItem {
  assignment_id: string
  job_id: string
  round_number: number
  round_type: RoundType
  deadline_at?: string | null
  status: AssignmentStatus
  schema_id?: string | null
  created_at: string
}

export interface AuditLogEntry {
  id: string
  job_id: string
  user_id?: string | null
  action: string
  details?: Record<string, unknown> | null
  created_at: string
}

// RBAC types
export type UserRole = 'viewer' | 'member' | 'reviewer' | 'approver' | 'admin'

export interface RoleAssignment {
  user_id: string
  role: UserRole
  status: 'assigned' | 'already_assigned'
}

export interface UserResponse {
  id: string
  email: string
  display_name?: string | null
  roles: UserRole[]
  created_at: string
}

export interface CurrentUserResponse {
  user_id: string
  workspace_id: string
  roles: UserRole[]
}

// Auth types
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest extends LoginRequest {
  name: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: string
  workspace_id: string
  roles: UserRole[]
}

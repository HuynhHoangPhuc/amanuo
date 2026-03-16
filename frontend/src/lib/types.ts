/** TypeScript types mirroring FastAPI Pydantic models. */

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed'
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
}

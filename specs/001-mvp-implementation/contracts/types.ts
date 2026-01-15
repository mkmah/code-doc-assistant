/**
 * TypeScript Types for Code Documentation Assistant API
 *
 * Generated from OpenAPI specification
 * Version: 1.0.0
 */

// ============================================================================
// Common Types
// ============================================================================

export type CodebaseStatus = 'queued' | 'processing' | 'completed' | 'failed';
export type SourceType = 'zip' | 'github_url';
export type IngestionStep = 'validating' | 'cloning' | 'parsing' | 'chunking' | 'embedding' | 'indexing' | 'complete';
export type MessageType = 'user' | 'assistant';
export type StreamEventType = 'chunk' | 'sources' | 'done' | 'error';

// ============================================================================
// Codebase Types
// ============================================================================

export interface Codebase {
  id: string;
  name: string;
  description: string | null;
  source_type: SourceType;
  source_url: string | null;
  status: CodebaseStatus;
  total_files: number;
  processed_files: number;
  primary_language: string | null;
  all_languages: string[] | null;
  size_bytes: number;
  error_message: string | null;
  workflow_id: string | null;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface UploadResponse {
  codebase_id: string;
  status: 'queued' | 'processing';
  workflow_id: string;
}

export interface CodebaseListResponse {
  codebases: Codebase[];
  total: number;
  page: number;
  limit: number;
}

export interface IngestionStatus {
  codebase_id: string;
  status: CodebaseStatus;
  progress: number; // 0-100
  total_files: number;
  processed_files: number;
  current_step: IngestionStep | null;
  error: string | null;
  secrets_detected: SecretDetection[] | null;
  started_at: string | null; // ISO 8601
  completed_at: string | null; // ISO 8601
}

export interface SecretDetection {
  file_path: string;
  secret_count: number;
}

export interface UploadCodebaseRequest {
  name: string;
  description?: string;
  file?: File; // ZIP or tar.gz
  repository_url?: string; // GitHub URL
}

// ============================================================================
// Chat Types
// ============================================================================

export interface ChatRequest {
  codebase_id: string;
  query: string;
  session_id?: string;
  stream?: boolean;
}

export interface Source {
  file_path: string;
  line_start: number;
  line_end: number;
  snippet?: string;
  confidence?: number;
}

export interface StreamEvent {
  type: StreamEventType;
  content?: string; // For type='chunk'
  sources?: Source[]; // For type='sources'
  error?: string; // For type='error'
}

export interface ChatMessage {
  message_id: string;
  session_id: string;
  role: MessageType;
  content: string;
  timestamp: string; // ISO 8601
  citations?: Source[];
  retrieved_chunks?: string[];
  token_count?: number;
}

export interface ChatSession {
  session_id: string;
  codebase_id: string;
  created_at: string;
  last_active: string;
  message_count: number;
  context_chunks?: string[];
}

// ============================================================================
// Health Types
// ============================================================================

export interface HealthResponse {
  status: 'healthy';
  version: string;
}

export interface ReadinessResponse {
  status: 'ready';
  dependencies: {
    chromadb: 'ok' | 'error';
    temporal: 'ok' | 'error';
  };
}

// ============================================================================
// Error Types
// ============================================================================

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface ErrorCodeMap {
  INVALID_FILE_TYPE: 'Only ZIP and tar.gz files are supported';
  FILE_TOO_LARGE: 'File size exceeds 100MB limit';
  INVALID_GITHUB_URL: 'Invalid GitHub repository URL';
  CODEBASE_NOT_FOUND: 'Codebase not found';
  INVALID_REQUEST: 'Invalid request parameters';
  SERVICE_UNAVAILABLE: 'Service temporarily unavailable';
  EMBEDDING_SERVICE_ERROR: 'Embedding generation failed, retrying';
  LLM_SERVICE_ERROR: 'LLM request failed';
}

// ============================================================================
// API Client Interface
// ============================================================================

export interface CodeDocAssistantClient {
  // Codebase operations
  uploadCodebase(request: UploadCodebaseRequest): Promise<UploadResponse>;
  listCodebases(page?: number, limit?: number): Promise<CodebaseListResponse>;
  getCodebase(codebaseId: string): Promise<Codebase>;
  deleteCodebase(codebaseId: string): Promise<void>;
  getCodebaseStatus(codebaseId: string): Promise<IngestionStatus>;

  // Chat operations
  chat(request: ChatRequest): Promise<AsyncIterable<StreamEvent>>;

  // Health operations
  healthCheck(): Promise<HealthResponse>;
  readinessCheck(): Promise<ReadinessResponse>;
}

// ============================================================================
// Utility Types
// ============================================================================

export type Prettify<T> = {
  [K in keyof T]: T[K];
} & {};

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K];
};

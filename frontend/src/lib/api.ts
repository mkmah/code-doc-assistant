const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface UploadResponse {
  codebase_id: string;
  status: "queued" | "processing";
  workflow_id: string;
}

export interface Codebase {
  id: string;
  name: string;
  description: string | null;
  source_type: "zip" | "github_url";
  source_url: string | null;
  status: "queued" | "processing" | "completed" | "failed";
  total_files: number;
  processed_files: number;
  primary_language: string | null;
  all_languages: string[] | null;
  size_bytes: number;
  error_message: string | null;
  workflow_id: string | null;
  progress?: number;
  created_at: string;
  updated_at: string;
}

export interface IngestionStatus {
  codebase_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  total_files: number;
  processed_files: number;
  current_step: string | null;
  error: string | null;
  secrets_detected: Array<{ file_path: string; secret_count: number }> | null;
  started_at: string | null;
  completed_at: string | null;
  primary_language: string | null;
}

export interface ChatRequest {
  codebase_id: string;
  query: string;
  session_id?: string;
  stream?: boolean;
}

export interface StreamEvent {
  type: "session_id" | "chunk" | "sources" | "done" | "error";
  session_id?: string;
  content?: string;
  sources?: Array<{
    file_path: string;
    line_start: number;
    line_end: number;
    snippet?: string;
    confidence?: number;
  }>;
  error?: string;
}

class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Upload error types for specific handling
 */
export enum UploadErrorType {
  FILE_TOO_LARGE = "FILE_TOO_LARGE",
  INVALID_FILE_TYPE = "INVALID_FILE_TYPE",
  CORRUPTED_ZIP = "CORRUPTED_ZIP",
  TEMPORAL_UNAVAILABLE = "TEMPORAL_UNAVAILABLE",
  NETWORK_ERROR = "NETWORK_ERROR",
  UNKNOWN = "UNKNOWN",
}

/**
 * Parse error response and determine error type
 */
function getUploadErrorType(statusCode: number, errorMessage: string): UploadErrorType {
  if (statusCode === 413) {
    return UploadErrorType.FILE_TOO_LARGE;
  }
  if (statusCode === 400) {
    if (
      errorMessage.includes("ZIP") ||
      errorMessage.includes("zip") ||
      errorMessage.includes("invalid")
    ) {
      return UploadErrorType.CORRUPTED_ZIP;
    }
    if (errorMessage.includes("file") || errorMessage.includes("Only")) {
      return UploadErrorType.INVALID_FILE_TYPE;
    }
  }
  if (statusCode === 500 || statusCode === 503) {
    if (errorMessage.includes("Temporal") || errorMessage.includes("workflow")) {
      return UploadErrorType.TEMPORAL_UNAVAILABLE;
    }
  }
  return UploadErrorType.UNKNOWN;
}

/**
 * Get user-friendly error message based on error type
 */
function getErrorMessage(errorType: UploadErrorType, details?: string): string {
  switch (errorType) {
    case UploadErrorType.FILE_TOO_LARGE:
      return "File size exceeds the 100MB limit. Please upload a smaller file.";
    case UploadErrorType.INVALID_FILE_TYPE:
      return "Invalid file type. Only ZIP and tar.gz files are supported.";
    case UploadErrorType.CORRUPTED_ZIP:
      return "The uploaded file is corrupted or not a valid archive. Please check the file and try again.";
    case UploadErrorType.TEMPORAL_UNAVAILABLE:
      return "The ingestion service is temporarily unavailable. Please try again in a few moments.";
    case UploadErrorType.NETWORK_ERROR:
      return "Network error. Please check your connection and try again.";
    default:
      return details || "Upload failed. Please try again.";
  }
}

/**
 * Upload a codebase for processing with enhanced error handling
 *
 * Handles specific error cases:
 * - Size limit (413): File exceeds 100MB
 * - Corrupted ZIP (400): Invalid archive format
 * - Temporal unavailable (500/503): Workflow service down
 */
export async function uploadCodebase(
  name: string,
  description?: string,
  file?: File,
  repositoryUrl?: string,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("name", name);
  if (description) formData.append("description", description);
  if (file) {
    // Validate file size client-side before upload
    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      throw new ApiError(
        UploadErrorType.FILE_TOO_LARGE,
        getErrorMessage(UploadErrorType.FILE_TOO_LARGE),
        { maxSize, fileSize: file.size },
      );
    }
    formData.append("file", file);
  }
  if (repositoryUrl) formData.append("repository_url", repositoryUrl);

  let response: Response;

  try {
    response = await fetch(`${API_URL}/api/v1/codebase/upload`, {
      method: "POST",
      body: formData,
    });
  } catch (error) {
    // Network or fetch errors
    throw new ApiError(
      UploadErrorType.NETWORK_ERROR,
      getErrorMessage(UploadErrorType.NETWORK_ERROR),
      { originalError: error },
    );
  }

  if (!response.ok) {
    const statusCode = response.status;
    let errorMessage = "";
    let errorDetails: Record<string, unknown> = {};

    try {
      const error = await response.json();
      errorMessage = error.error?.message || error.message || "";
      errorDetails = error.error?.details || error.details || {};
    } catch {
      errorMessage = `HTTP ${statusCode}`;
      errorDetails = { statusCode };
    }

    const errorType = getUploadErrorType(statusCode, errorMessage);
    const userMessage = getErrorMessage(errorType, errorMessage);

    throw new ApiError(errorType, userMessage, { ...errorDetails, statusCode });
  }

  return response.json();
}

/**
 * List all codebases
 */
export async function listCodebases(
  page = 1,
  limit = 5,
): Promise<{ codebases: Codebase[]; total: number; page: number; limit: number }> {
  const params = new URLSearchParams({ page: page.toString(), limit: limit.toString() });
  const response = await fetch(`${API_URL}/api/v1/codebase?${params}`);

  if (!response.ok) {
    throw new ApiError("LIST_FAILED", "Failed to list codebases");
  }

  return response.json();
}

/**
 * Get a specific codebase
 */
export async function getCodebase(codebaseId: string): Promise<Codebase> {
  const response = await fetch(`${API_URL}/api/v1/codebase/${codebaseId}`);

  if (!response.ok) {
    throw new ApiError("NOT_FOUND", "Codebase not found");
  }

  return response.json();
}

/**
 * Get ingestion status for a codebase
 */
export async function getCodebaseStatus(codebaseId: string): Promise<IngestionStatus> {
  const response = await fetch(`${API_URL}/api/v1/codebase/${codebaseId}/status`);

  if (!response.ok) {
    throw new ApiError("STATUS_FAILED", "Failed to get status");
  }

  return response.json();
}

/**
 * Delete a codebase
 */
export async function deleteCodebase(codebaseId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/codebase/${codebaseId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new ApiError("DELETE_FAILED", "Failed to delete codebase");
  }
}

/**
 * Query a codebase with streaming response
 */
export async function* chatCodebase(
  request: ChatRequest,
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new ApiError("CHAT_FAILED", "Chat request failed");
  }

  const reader = response.body?.getReader();
  if (!reader) throw new ApiError("STREAM_FAILED", "No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        try {
          const event = JSON.parse(data) as StreamEvent;
          yield event;
          if (event.type === "done" || event.type === "error") {
            return;
          }
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}

/**
 * Readiness check
 */
export async function readinessCheck(): Promise<{
  status: string;
  dependencies: { chromadb: string; temporal: string };
}> {
  const response = await fetch(`${API_URL}/health/ready`);
  return response.json();
}

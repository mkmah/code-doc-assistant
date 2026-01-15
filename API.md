# API Documentation

## Overview

The Code Documentation Assistant API is a RESTful API built with FastAPI. It provides endpoints for codebase ingestion, querying, and status monitoring.

**Base URL**: `http://localhost:8000`

**Interactive Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Content Type**: `application/json` (except where noted)

## Authentication

Currently, the API does not require authentication for MVP. Future versions will include API key or OAuth authentication.

## Response Format

### Success Response

```json
{
  "field": "value"
}
```

### Error Response

```json
{
  "error": {
    "message": "Error description",
    "type": "ErrorType",
    "details": {}
  }
}
```

## Endpoints

### Health Check

#### GET /health

Check if the API is running.

**Response**: `200 OK`

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### GET /health/ready

Check if the API is ready to accept requests (includes dependency checks).

**Response**: `200 OK`

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "temporal": "ok",
    "chromadb": "ok"
  }
}
```

### Codebase Management

#### POST /api/v1/codebase/upload

Upload a codebase for ingestion. Accepts either a ZIP file or a GitHub URL.

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Human-readable name for the codebase |
| file | file | No* | ZIP file containing source code |
| github_url | string | No* | Public GitHub repository URL |
| branch | string | No | Git branch to clone (default: main) |

*Either `file` or `github_url` must be provided.

**Example: Upload ZIP**

```bash
curl -X POST http://localhost:8000/api/v1/codebase/upload \
  -F "name=My Codebase" \
  -F "file=@codebase.zip"
```

**Example: Upload from GitHub**

```bash
curl -X POST http://localhost:8000/api/v1/codebase/upload \
  -F "name=My Repo" \
  -F "github_url=https://github.com/user/repo" \
  -F "branch=develop"
```

**Response**: `202 Accepted`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Codebase",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors**:
- `400 Bad Request`: Missing both file and github_url
- `422 Unprocessable Entity`: Invalid ZIP file or GitHub URL

#### GET /api/v1/codebase

List all codebases with pagination.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 10 | Number of items per page |
| offset | integer | 0 | Number of items to skip |

**Example**:

```bash
curl http://localhost:8000/api/v1/codebase?limit=20&offset=0
```

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Codebase",
      "status": "ready",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z",
      "total_files": 150,
      "total_chunks": 500,
      "primary_language": "Python"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### GET /api/v1/codebase/{id}

Get details for a specific codebase.

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string (UUID) | Codebase ID |

**Example**:

```bash
curl http://localhost:8000/api/v1/codebase/550e8400-e29b-41d4-a716-446655440000
```

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Codebase",
  "status": "ready",
  "source": {
    "type": "github",
    "url": "https://github.com/user/repo",
    "branch": "main"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "total_files": 150,
  "total_chunks": 500,
  "primary_language": "Python",
  "languages": ["Python", "JavaScript", "TypeScript"],
  "ingestion_status": {
    "status": "completed",
    "progress": 1.0,
    "current_step": "complete",
    "total_files": 150,
    "processed_files": 150
  }
}
```

**Errors**:
- `404 Not Found`: Codebase not found

#### GET /api/v1/codebase/{id}/status

Get the ingestion status for a codebase.

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string (UUID) | Codebase ID |

**Example**:

```bash
curl http://localhost:8000/api/v1/codebase/550e8400-e29b-41d4-a716-446655440000/status
```

**Response**: `200 OK`

```json
{
  "status": "processing",
  "current_step": "embedding",
  "progress": 0.7,
  "total_files": 150,
  "processed_files": 105,
  "total_chunks": 400,
  "processed_chunks": 280,
  "secrets_detected": [
    {
      "file_path": "config.py",
      "secret_type": "AWS_API_KEY",
      "secret_count": 1
    }
  ]
}
```

**Status Values**:
- `pending`: Queued for processing
- `validating`: Validating input
- `cloning`: Cloning/extracting files
- `parsing`: Parsing code with Tree-sitter
- `chunking`: Creating semantic chunks
- `embedding`: Generating embeddings
- `indexing`: Indexing in vector store
- `completed`: Processing complete
- `failed`: Processing failed

**Completed Response**:

```json
{
  "status": "completed",
  "current_step": "complete",
  "progress": 1.0,
  "total_files": 150,
  "processed_files": 150,
  "primary_language": "Python",
  "languages": ["Python", "JavaScript"]
}
```

**Failed Response**:

```json
{
  "status": "failed",
  "current_step": "parsing",
  "progress": 0.3,
  "error": "Failed to parse file: invalid syntax",
  "total_files": 150,
  "processed_files": 45
}
```

#### DELETE /api/v1/codebase/{id}

Delete a codebase and all associated data.

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string (UUID) | Codebase ID |

**Example**:

```bash
curl -X DELETE http://localhost:8000/api/v1/codebase/550e8400-e29b-41d4-a716-446655440000
```

**Response**: `204 No Content`

**Errors**:
- `404 Not Found`: Codebase not found

### Chat/Query

#### POST /api/v1/chat

Query a codebase with a natural language question. Returns a Server-Sent Events (SSE) stream.

**Request Headers**:
- `Content-Type: application/json`

**Request Body**:

```json
{
  "codebase_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "How does authentication work?",
  "session_id": "optional-session-id"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| codebase_id | string (UUID) | Yes | Codebase to query |
| query | string | Yes | Natural language question |
| session_id | string | No | Session ID for conversation history |

**Response**: `200 OK` (text/event-stream)

The response is a Server-Sent Events stream. Each event is JSON-encoded:

**Chunk Event** (streaming response):

```
data: {"type":"chunk","content":"The authentication"}

data: {"type":"chunk","content":" system uses"}

data: {"type":"chunk","content":" JWT tokens..."}
```

**Sources Event** (citations):

```
data: {"type":"sources","sources":[
  {
    "file_path": "app/auth.py",
    "line_start": 45,
    "line_end": 60,
    "snippet": "def verify_token(token):..."
  }
]}
```

**Error Event**:

```
data: {"type":"error","error":"Failed to process query"}
```

**Done Event**:

```
data: {"type":"done"}
```

**Example with curl**:

```bash
curl -N http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "codebase_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "How does authentication work?"
  }'
```

**Example with JavaScript**:

```javascript
const response = await fetch('http://localhost:8000/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    codebase_id: '550e8400-e29b-41d4-a716-446655440000',
    query: 'How does authentication work?'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      if (event.type === 'chunk') {
        console.log(event.content);
      } else if (event.type === 'sources') {
        console.log('Sources:', event.sources);
      }
    }
  }
}
```

**Errors**:
- `400 Bad Request`: Invalid request body
- `404 Not Found`: Codebase not found
- `422 Unprocessable Entity`: Codebase not ready for querying

## Metrics

#### GET /metrics

Get Prometheus metrics for monitoring.

**Response**: `200 OK` (text/plain)

Prometheus metrics in text format:

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/codebase",status_code="200"} 42.0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="POST",endpoint="/api/v1/chat",le="0.1"} 5.0
http_request_duration_seconds_bucket{method="POST",endpoint="/api/v1/chat",le="0.5"} 23.0
...
```

## Data Models

### Codebase

```typescript
{
  id: string;              // UUID
  name: string;            // Human-readable name
  status: string;          // "pending" | "processing" | "ready" | "failed"
  source?: {
    type: string;          // "zip" | "github"
    url?: string;          // GitHub URL (if applicable)
    branch?: string;       // Git branch (if applicable)
  };
  created_at: string;      // ISO 8601 timestamp
  updated_at: string;      // ISO 8601 timestamp
  total_files?: number;    // Total files in codebase
  total_chunks?: number;   // Total chunks created
  primary_language?: string; // Primary language detected
  languages?: string[];    // All languages detected
  ingestion_status?: IngestionStatus;
}
```

### IngestionStatus

```typescript
{
  status: string;          // "pending" | "validating" | "cloning" | "parsing" |
                          // "chunking" | "embedding" | "indexing" |
                          // "completed" | "failed"
  current_step: string;    // Current processing step
  progress: number;        // 0.0 to 1.0
  total_files: number;     // Total files to process
  processed_files: number; // Files processed so far
  total_chunks?: number;   // Total chunks to create
  processed_chunks?: number; // Chunks processed so far
  primary_language?: string; // Primary language detected
  languages?: string[];    // All languages detected
  secrets_detected?: SecretDetection[];
  error?: string;          // Error message (if failed)
}
```

### SecretDetection

```typescript
{
  file_path: string;       // Path to file containing secret
  secret_type: string;     // Type of secret (e.g., "AWS_API_KEY")
  secret_count: number;    // Number of secrets found
}
```

### Source

```typescript
{
  file_path: string;       // Path to source file
  line_start: number;      // Start line number
  line_end: number;        // End line number
  snippet?: string;        // Code snippet (optional)
}
```

### StreamEvent

```typescript
// Chunk event (streaming content)
{
  type: "chunk";
  content: string;         // Response content chunk
}

// Sources event (citations)
{
  type: "sources";
  sources: Source[];       // Array of source citations
}

// Error event
{
  type: "error";
  error: string;           // Error message
}

// Done event
{
  type: "done";
}
```

## Error Codes

| Status Code | Type | Description |
|-------------|------|-------------|
| 400 | BadRequest | Invalid request format |
| 404 | NotFound | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | UnprocessableEntity | Validation failed |
| 429 | RateLimitExceeded | Too many requests |
| 500 | InternalServerError | Unexpected error |
| 503 | ServiceUnavailable | External service error |

## Rate Limiting

Currently not enforced in MVP. Future versions will include:
- 100 requests per minute per IP
- 1000 requests per day per IP

## Versioning

The API is versioned using URL paths (e.g., `/api/v1/`). Major version changes will be reflected in the URL.

## Changelog

### v1.0.0 (2024-01-15)
- Initial release
- Codebase upload (ZIP and GitHub)
- Status tracking
- Chat/query with SSE streaming
- Health check endpoints

## Support

For API issues or questions, please open an issue on GitHub.

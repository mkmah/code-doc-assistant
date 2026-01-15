# Product Requirements Document (PRD)
## Code Documentation Assistant

---

## 1. Executive Summary

### 1.1 Project Overview
A conversational AI assistant that ingests codebases (GitHub repositories or local files) and answers questions about code structure, functionality, API endpoints, dependencies, and implementation details using RAG (Retrieval Augmented Generation).

### 1.2 Objectives
- Enable developers to quickly understand unfamiliar codebases
- Reduce onboarding time for new team members
- Provide intelligent code search and documentation capabilities
- Demonstrate production-ready engineering practices

### 1.3 Success Metrics
- Query response time < 3 seconds for 90% of requests
- Retrieval accuracy > 85% (relevant code chunks returned)
- System uptime > 99% in production
- Support for codebases up to 100MB initially

---

## 2. Technical Stack

### 2.1 Backend Services
- **Language**: Python 3.11+
- **API Framework**: FastAPI (async support, automatic OpenAPI docs)
- **Orchestration**: Temporal (workflow management, retry logic, observability)
- **Agent Framework**: LangGraph (state management, agent workflows)
- **Vector Database**: ChromaDB (local development + persistent storage)
- **LLM Provider**: Anthropic Claude (Sonnet 4 for intelligence)
- **Embeddings**: `jina-embeddings-v4` (Jina AI) or fallback to `text-embedding-3-small` (OpenAI)
- **Package Manager**: uv

### 2.2 Frontend Application
- **Framework**: TanStack Start (React-based, full-stack)
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: TanStack Query (React Query)
- **Type Safety**: TypeScript
- **Package Manager**: bun

### 2.3 Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (local: Docker Desktop K8s)
- **Local Development**: Tilt (automated dev environment)
- **CI/CD**: GitHub Actions
- **Observability**: Prometheus + Grafana, OpenTelemetry

---

## 3. Folder Structure

```
code-doc-assistant/
├── frontend/                       # TanStack Start application
│   ├── app/
│   │   ├── routes/
│   │   │   ├── index.tsx          # Home page
│   │   │   ├── chat.tsx           # Chat interface
│   │   │   └── upload.tsx         # Codebase upload
│   │   ├── components/
│   │   │   ├── ui/                # shadcn components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── CodeViewer.tsx
│   │   │   └── UploadForm.tsx
│   │   ├── lib/
│   │   │   ├── api.ts             # API client
│   │   │   └── utils.ts
│   │   ├── styles/
│   │   │   └── globals.css
│   │   └── root.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                        # FastAPI services
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py        # Chat endpoints
│   │   │   │   ├── upload.py      # Upload endpoints
│   │   │   │   └── health.py      # Health checks
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py          # Configuration
│   │   │   ├── logging.py         # Logging setup
│   │   │   └── security.py        # Auth/Security
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── codebase_processor.py  # Code parsing
│   │   │   ├── embedding_service.py   # Embedding generation
│   │   │   ├── vector_store.py        # ChromaDB operations
│   │   │   └── llm_service.py         # LLM interactions
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py           # LangGraph agent definition
│   │   │   ├── nodes.py           # Agent nodes
│   │   │   └── tools.py           # Agent tools
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py         # Pydantic models
│   │   │   └── db_models.py       # Database models
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── code_parser.py     # AST parsing utilities
│   │   │   ├── chunking.py        # Code chunking strategies
│   │   │   └── validators.py      # Input validation
│   │   └── main.py                # FastAPI app entry
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── pyproject.toml
│   └── Dockerfile
│
├── temporal/                       # Temporal workflows
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── ingestion_workflow.py  # Code ingestion workflow
│   │   └── query_workflow.py      # Query processing workflow
│   ├── activities/
│   │   ├── __init__.py
│   │   ├── parse_activities.py
│   │   ├── embed_activities.py
│   │   └── index_activities.py
│   ├── worker.py
│   └── Dockerfile
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml     # Local development
│   │   └── docker-compose.prod.yml
│   ├── k8s/
│   │   ├── base/
│   │   │   ├── namespace.yaml
│   │   │   ├── configmap.yaml
│   │   │   ├── secrets.yaml
│   │   │   ├── backend-deployment.yaml
│   │   │   ├── backend-service.yaml
│   │   │   ├── frontend-deployment.yaml
│   │   │   ├── frontend-service.yaml
│   │   │   ├── temporal-deployment.yaml
│   │   │   ├── chromadb-deployment.yaml
│   │   │   ├── chromadb-pvc.yaml
│   │   │   └── ingress.yaml
│   │   ├── overlays/
│   │   │   ├── dev/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── kustomization.yaml
│   ├── monitoring/
│   │   ├── prometheus.yaml
│   │   ├── grafana.yaml
│   │   └── dashboards/
│   └── Tiltfile                    # Local dev automation
│
├── scripts/
│   ├── setup.sh                    # Environment setup
│   ├── seed_data.sh               # Sample data seeding
│   └── deploy.sh                  # Deployment script
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI pipeline
│       ├── cd.yml                 # CD pipeline
│       └── test.yml               # Test automation
│
├── .gitignore
├── README.md
├── LICENSE
└── Makefile                       # Common commands
```

---

## 4. Code Ingestion & Processing Strategy

### 4.1 Codebase Parsing Libraries

#### **Recommended: Tree-sitter** (BEST CHOICE)
- **Why**: Language-agnostic, production-ready, fast incremental parsing
- **Library**: `py-tree-sitter`
- **Pros**:
  - Supports 40+ languages with official grammars
  - Parses code into concrete syntax trees (CST)
  - Error-tolerant (handles incomplete/buggy code)
  - Used by GitHub, Atom, Neovim
- **Use Cases**: Extract functions, classes, imports, comments, docstrings

### 4.2 Chunking Strategy

#### **Semantic Code Chunking** (RECOMMENDED)
Use Tree-sitter to create semantically meaningful chunks:

```python
# Chunk Hierarchy (in priority order):
1. Function/Method level (most granular)
   - Include docstrings, type hints, decorators
   - Size: ~50-200 lines typically

2. Class level
   - Include class docstring and all methods
   - Split large classes into method groups

3. Module level metadata
   - Imports, module docstrings, global variables
   
4. File-level context
   - File path, language, dependencies
```

#### Chunking Parameters:
- **Target chunk size**: 512-1024 tokens (with overlap)
- **Overlap**: 50-100 tokens (preserve context)
- **Max chunk size**: 1500 tokens (LLM context efficiency)

#### Metadata to Store:
```python
{
    "content": "actual code",
    "language": "python",
    "file_path": "src/services/auth.py",
    "type": "function",  # function, class, method, import
    "name": "authenticate_user",
    "line_start": 45,
    "line_end": 67,
    "dependencies": ["jwt", "bcrypt"],
    "docstring": "...",
    "parent_class": "AuthService",  # if method
    "imports": ["from typing import Optional"],
    "complexity": 5  # cyclomatic complexity
}
```

---

## 5. System Architecture

### 5.1 High-Level Design (HLD)

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                    (TanStack Start Frontend)                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTPS/REST
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway / Ingress                      │
│                    (Kubernetes Ingress/Nginx)                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌──────────────────┐   ┌──────────────────┐
│   FastAPI Backend│   │  Temporal Server │
│   (API Layer)    │◄──┤   (Workflows)    │
└────┬─────────────┘   └──────────────────┘
     │                         │
     │                         │ Triggers workflows
     │                         ▼
     │                  ┌──────────────────┐
     │                  │ Temporal Workers │
     │                  │  (Activities)    │
     │                  └──────┬───────────┘
     │                         │
     │   ┌─────────────────────┼─────────────────────┐
     │   │                     │                     │
     ▼   ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  LangGraph   │      │  ChromaDB    │      │ LLM Service  │
│   Agent      │─────►│ Vector Store │      │  (Claude)    │
│  Executor    │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
     │                                               │
     └───────────────────────────────────────────────┘
                    Orchestrates
                    
┌─────────────────────────────────────────────────────────────────┐
│                      Observability Layer                        │
│   Prometheus (Metrics) | Grafana (Viz) | OpenTelemetry (Traces)│
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Low-Level Design (LLD)

#### **Component 1: Ingestion Pipeline**

```
GitHub URL/Local Files
        │
        ▼
┌───────────────────────┐
│  Upload Endpoint      │
│  POST /api/v1/upload  │
└──────────┬────────────┘
           │
           │ Triggers Temporal Workflow
           ▼
┌────────────────────────────────────────┐
│    Ingestion Workflow (Temporal)       │
│                                        │
│  1. ValidateCodebase Activity          │
│     - Check file types                 │
│     - Validate size limits             │
│     - Scan for secrets (git-secrets)   │
│                                        │
│  2. CloneRepository Activity           │
│     - Git clone (if URL)               │
│     - Extract files                    │
│                                        │
│  3. ParseCodebase Activity             │
│     - Tree-sitter parsing              │
│     - Extract functions/classes        │
│     - Generate metadata                │
│                                        │
│  4. ChunkCode Activity                 │
│     - Semantic chunking                │
│     - Add overlaps                     │
│     - Enrich with metadata             │
│                                        │
│  5. GenerateEmbeddings Activity        │
│     - Batch embed chunks               │
│     - Rate limit handling              │
│                                        │
│  6. IndexToVectorStore Activity        │
│     - Upsert to ChromaDB               │
│     - Create metadata indexes          │
│                                        │
└────────────────┬───────────────────────┘
                 │
                 ▼
         ┌──────────────┐
         │  ChromaDB    │
         │ (Persistent) │
         └──────────────┘
```

#### **Component 2: Query Pipeline**

```
User Query
    │
    ▼
┌────────────────────────┐
│ POST /api/v1/chat      │
│                        │
│ {                      │
│   "query": "...",      │
│   "session_id": "...", │
│   "codebase_id": "..." │
│ }                      │
└───────────┬────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│      LangGraph Agent Graph          │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  1. Query Analysis Node     │   │
│  │     - Intent classification  │   │
│  │     - Extract entities       │   │
│  │     - Rewrite query          │   │
│  └───────────┬─────────────────┘   │
│              │                     │
│              ▼                     │
│  ┌─────────────────────────────┐   │
│  │  2. Retrieval Node          │   │
│  │     - Semantic search        │   │
│  │     - Hybrid search (BM25)   │   │
│  │     - Re-ranking             │   │
│  └───────────┬─────────────────┘   │
│              │                     │
│              ▼                     │
│  ┌─────────────────────────────┐   │
│  │  3. Context Building Node   │   │
│  │     - Format retrieved code  │   │
│  │     - Add file context       │   │
│  │     - Include dependencies   │   │
│  └───────────┬─────────────────┘   │
│              │                     │
│              ▼                     │
│  ┌─────────────────────────────┐   │
│  │  4. Response Generation     │   │
│  │     - Call Claude API        │   │
│  │     - Stream response        │   │
│  │     - Extract citations      │   │
│  └───────────┬─────────────────┘   │
│              │                     │
│              ▼                     │
│  ┌─────────────────────────────┐   │
│  │  5. Validation Node         │   │
│  │     - Hallucination check    │   │
│  │     - Cite sources           │   │
│  │     - Confidence score       │   │
│  └───────────┬─────────────────┘   │
│              │                     │
└──────────────┼─────────────────────┘
               │
               ▼
          Response to User
```

#### **Component 3: Vector Store Design**

```
ChromaDB Collections:

Collection: "code_chunks"
├── Embeddings (vector)
├── Metadata:
│   ├── codebase_id (indexed)
│   ├── file_path (indexed)
│   ├── language (indexed)
│   ├── chunk_type (function/class/etc)
│   ├── name
│   ├── line_range
│   ├── dependencies
│   └── timestamp

Query Strategies:
1. Semantic Search: cosine similarity on embeddings
2. Metadata Filtering: language, file_path, type
3. Hybrid Search: Combine dense + sparse (BM25)
4. Re-ranking: Cross-encoder for top-k results
```

---

## 6. API Specifications

### 6.1 Core Endpoints

#### Upload Codebase
```http
POST /api/v1/codebase/upload
Content-Type: multipart/form-data

Parameters:
- file: ZIP file or tar.gz
- repository_url: string (optional, GitHub URL)
- name: string
- description: string (optional)

Response:
{
  "codebase_id": "uuid",
  "status": "processing",
  "workflow_id": "temporal-workflow-id"
}
```

#### Check Ingestion Status
```http
GET /api/v1/codebase/{codebase_id}/status

Response:
{
  "codebase_id": "uuid",
  "status": "completed|processing|failed",
  "progress": 85,
  "files_processed": 120,
  "total_files": 142,
  "error": null
}
```

#### Chat Query
```http
POST /api/v1/chat
Content-Type: application/json

{
  "codebase_id": "uuid",
  "query": "How does the authentication work?",
  "session_id": "session-uuid",
  "stream": true
}

Response (Stream):
data: {"type": "chunk", "content": "The authentication..."}
data: {"type": "chunk", "content": " is implemented using..."}
data: {"type": "sources", "sources": [...]}
data: {"type": "done"}
```

#### List Codebases
```http
GET /api/v1/codebase?page=1&limit=20

Response:
{
  "codebases": [
    {
      "id": "uuid",
      "name": "My Project",
      "language": "python",
      "files_count": 142,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 50,
  "page": 1
}
```

---

## 7. Deployment Architecture

### 7.1 Docker Compose (Local Development)

```yaml
# docker-compose.yml
version: '3.9'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - CHROMADB_HOST=chromadb
      - TEMPORAL_HOST=temporal
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./backend:/app
    depends_on:
      - chromadb
      - temporal

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - ANONYMIZED_TELEMETRY=False

  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
      - "8088:8088"  # Web UI
    environment:
      - DB=postgresql
      - POSTGRES_SEEDS=postgres
    depends_on:
      - postgres

  temporal-worker:
    build: ./temporal
    environment:
      - TEMPORAL_HOST=temporal:7233
    depends_on:
      - temporal

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=temporal
      - POSTGRES_USER=temporal
    volumes:
      - postgres_data:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./infra/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infra/monitoring/dashboards:/etc/grafana/provisioning/dashboards

volumes:
  chromadb_data:
  postgres_data:
  prometheus_data:
  grafana_data:
```

### 7.2 Kubernetes Manifests

#### Backend Deployment
```yaml
# k8s/base/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: code-doc-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: code-doc-assistant/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: CHROMADB_HOST
          value: "chromadb-service"
        - name: TEMPORAL_HOST
          value: "temporal-service:7233"
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: anthropic-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### ChromaDB StatefulSet
```yaml
# k8s/base/chromadb-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: chromadb
  namespace: code-doc-assistant
spec:
  serviceName: chromadb
  replicas: 1
  selector:
    matchLabels:
      app: chromadb
  template:
    metadata:
      labels:
        app: chromadb
    spec:
      containers:
      - name: chromadb
        image: chromadb/chroma:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: chromadb-storage
          mountPath: /chroma/chroma
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
  volumeClaimTemplates:
  - metadata:
      name: chromadb-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 50Gi
```

#### Ingress
```yaml
# k8s/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-ingress
  namespace: code-doc-assistant
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - code-assistant.yourdomain.com
    secretName: tls-secret
  rules:
  - host: code-assistant.yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3000
```

### 7.3 Tiltfile (Local Development)

```python
# Tiltfile
# Load Kubernetes YAML
k8s_yaml(['infra/k8s/base/namespace.yaml',
          'infra/k8s/base/configmap.yaml',
          'infra/k8s/base/secrets.yaml'])

# Backend Service
docker_build('code-doc-assistant/backend',
             './backend',
             dockerfile='./backend/Dockerfile',
             live_update=[
                 sync('./backend/app', '/app/app'),
                 run('pip install -r requirements.txt',
                     trigger='./backend/requirements.txt')
             ])

k8s_yaml('infra/k8s/base/backend-deployment.yaml')
k8s_yaml('infra/k8s/base/backend-service.yaml')
k8s_resource('backend',
             port_forwards='8000:8000',
             labels=['backend'])

# Frontend Service
docker_build('code-doc-assistant/frontend',
             './frontend',
             dockerfile='./frontend/Dockerfile',
             live_update=[
                 sync('./frontend/app', '/app/app'),
                 sync('./frontend/public', '/app/public')
             ])

k8s_yaml('infra/k8s/base/frontend-deployment.yaml')
k8s_yaml('infra/k8s/base/frontend-service.yaml')
k8s_resource('frontend',
             port_forwards='3000:3000',
             labels=['frontend'])

# ChromaDB
k8s_yaml('infra/k8s/base/chromadb-deployment.yaml')
k8s_yaml('infra/k8s/base/chromadb-pvc.yaml')
k8s_resource('chromadb',
             port_forwards='8001:8000',
             labels=['storage'])

# Temporal
k8s_yaml('infra/k8s/base/temporal-deployment.yaml')
k8s_resource('temporal',
             port_forwards=['7233:7233', '8088:8088'],
             labels=['orchestration'])

# Temporal Worker
docker_build('code-doc-assistant/temporal-worker',
             './temporal',
             dockerfile='./temporal/Dockerfile')
k8s_yaml('infra/k8s/base/temporal-worker-deployment.yaml')
k8s_resource('temporal-worker',
             labels=['orchestration'])

# Monitoring
k8s_yaml('infra/monitoring/prometheus.yaml')
k8s_yaml('infra/monitoring/grafana.yaml')
k8s_resource('prometheus',
             port_forwards='9090:9090',
             labels=['monitoring'])
k8s_resource('grafana',
             port_forwards='3001:3000',
             labels=['monitoring'])

# Custom button to seed sample data
local_resource('seed-data',
               'bash scripts/seed_data.sh',
               deps=['scripts/seed_data.sh'],
               labels=['setup'])
```

### 7.4 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        cd backend
        pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  test-frontend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'
    
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run tests
      run: |
        cd frontend
        npm run test

  build-and-push:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    
    - name: Login to DockerHub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push backend
      uses: docker/build-push-action@v4
      with:
        context: ./backend
        push: true
        tags: yourusername/code-doc-backend:${{ github.sha }},yourusername/code-doc-backend:latest
    
    - name: Build and push frontend
      uses: docker/build-push-action@v4
      with:
        context: ./frontend
        push: true
        tags: yourusername/code-doc-frontend:${{ github.sha }},yourusername/code-doc-frontend:latest
```

```yaml
# .github/workflows/cd.yml
name: CD Pipeline

on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types:
      - completed
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        kubeconfig: ${{ secrets.KUBE_CONFIG }}
    
    - name: Deploy to staging
      run: |
        kubectl apply -k infra/k8s/overlays/staging/
        kubectl rollout status deployment/backend -n code-doc-assistant-staging
        kubectl rollout status deployment/frontend -n code-doc-assistant-staging
    
    - name: Run smoke tests
      run: |
        bash scripts/smoke_tests.sh staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        kubeconfig: ${{ secrets.KUBE_CONFIG_PROD }}
    
    - name: Deploy to production
      run: |
        kubectl apply -k infra/k8s/overlays/production/
        kubectl rollout status deployment/backend -n code-doc-assistant
        kubectl rollout status deployment/frontend -n code-doc-assistant
```

---

## 8. RAG/LLM Approach & Decisions

### 8.1 Embedding Model Selection

**Decision: Voyage-Code-2**

| Model | Pros | Cons | Decision |
|-------|------|------|----------|
| jina-embeddings-v4 | Optimized for code, SOTA on code search | Paid API | ✅ PRIMARY |
| text-embedding-3-small | Cost-effective, fast, OpenAI | Not code-specific | 🔄 FALLBACK |

**Rationale**: Jina Embeddings v4 has the best performance

### 8.2 LLM Selection

**Decision: Claude Sonnet 4**

| Model | Context | Speed | Code Understanding | Cost |
|-------|---------|-------|-------------------|------|
| Claude Sonnet 4 | 200K | Fast | Excellent | $3/$15 |
| GPT-4 Turbo | 128K | Medium | Very Good | $10/$30 |
| Gemini 1.5 Pro | 1M | Slow | Good | $3.50/$10.50 |

**Rationale**: 
- Best code understanding (trains on GitHub data)
- Large context window for codebase understanding
- Streaming support for better UX
- Cost-effective for production

### 8.3 Vector Database Selection

**Decision: ChromaDB**

| Database | Pros | Cons | Decision |
|----------|------|------|----------|
| ChromaDB | Simple, local-first, Python-native | Limited scaling | ✅ PRIMARY |
| Pinecone | Managed, scalable | Vendor lock-in, cost | 🔄 PRODUCTION |
| Weaviate | Open-source, features | Complex setup | ❌ |
| Qdrant | Fast, Rust-based | Newer, less docs | ❌ |

**Rationale**: ChromaDB for MVP due to simplicity. Plan migration to Pinecone for production scale (>1M vectors).

### 8.4 Retrieval Strategy

**Hybrid Search Approach**:

1. **Dense Retrieval** (Semantic):
   - Embedding similarity (cosine)
   - Top-k: 20 candidates

2. **Sparse Retrieval** (Keyword):
   - BM25 on function/class names
   - Exact match on identifiers

3. **Re-ranking**:
   - Cross-encoder scoring
   - Final top-5 results

4. **Metadata Filtering**:
   - Language, file path, chunk type

```python
# Pseudo-code
candidates_dense = vector_search(query_embedding, top_k=20)
candidates_sparse = bm25_search(query_keywords, top_k=20)
candidates_merged = merge_and_dedupe(candidates_dense, candidates_sparse)
final_results = rerank(candidates_merged, query, top_k=5)
```

### 8.5 Prompt Engineering Strategy

**System Prompt Template**:
```
You are an expert code documentation assistant. Your role is to help developers understand codebases by analyzing the provided code snippets.

CONTEXT:
{retrieved_code_chunks}

INSTRUCTIONS:
1. Answer based ONLY on the provided code
2. Cite specific files and line numbers
3. Explain technical concepts clearly
4. If uncertain, say "I don't see this in the provided code"
5. For "how does X work" questions, trace through the code execution

QUERY: {user_query}
```

**Few-shot Examples**:
Include 2-3 examples of good Q&A pairs in system prompt.

### 8.6 Context Management

**Challenges**:
- Large files exceed LLM context
- Need to preserve code relationships
- Balance detail vs context limits

**Solution**:
- **Smart chunking**: Keep functions intact
- **Contextual snippets**: Include imports, class definitions
- **Hierarchical retrieval**: Fetch file → function → implementation
- **Context compression**: Use Claude's extended thinking for summarization

### 8.7 Guardrails

1. **Input Validation**:
   - Max file size: 100MB
   - Allowed file extensions
   - Secret scanning (git-secrets, trufflehog)

2. **Output Validation**:
   - Hallucination detection (check if code exists)
   - Citation verification (line numbers valid)
   - Confidence scoring

3. **Rate Limiting**:
   - 100 requests/hour per user
   - 10 concurrent queries max

4. **Content Safety**:
   - No private API keys in responses
   - Filter sensitive file paths

### 8.8 Quality Controls

**Metrics**:
- **Retrieval Accuracy**: % of queries with relevant code in top-5
- **Response Relevance**: LLM-as-judge scoring
- **Citation Accuracy**: % of cited lines that exist
- **Latency**: p95 < 3s

**Evaluation Dataset**:
- 100 curated Q&A pairs per language
- Weekly human evaluation (5 random queries/day)

**Continuous Improvement**:
- Log failed queries (no relevant retrieval)
- A/B test prompt variations
- Retrain embeddings on domain-specific code

### 8.9 Observability

**Instrumentation**:
```python
# OpenTelemetry tracing
@tracer.start_as_current_span("retrieve_code")
def retrieve_code(query: str):
    span = trace.get_current_span()
    span.set_attribute("query.length", len(query))
    span.set_attribute("results.count", len(results))
    return results
```

**Metrics** (Prometheus):
- `query_latency_seconds` (histogram)
- `retrieval_accuracy` (gauge)
- `llm_token_usage` (counter)
- `chromadb_query_duration` (histogram)

**Dashboards** (Grafana):
- Real-time query volume
- Retrieval quality trends
- Cost per query
- Error rates by component

**Logging** (Structured):
```python
logger.info(
    "Query processed",
    extra={
        "query_id": query_id,
        "codebase_id": codebase_id,
        "retrieval_time": 0.45,
        "llm_time": 2.3,
        "total_time": 2.75,
        "chunks_retrieved": 5,
        "tokens_used": 1523
    }
)
```

---

## 9. Key Technical Decisions

### 9.1 Architecture Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Microservices over Monolith** | Independent scaling, tech flexibility | Complexity, network overhead |
| **Temporal for workflows** | Durable execution, visibility, retries | Learning curve, infra overhead |
| **ChromaDB for MVP** | Simplicity, local development | Limited scale, need migration later |
| **FastAPI for backend** | Async, performance, auto docs | Less mature than Flask |
| **TanStack Start for frontend** | Modern React, SSR, file-based routing | Newer ecosystem |

### 9.2 Code Parsing Decision

**Tree-sitter over AST**:
- **Pros**: Multi-language, error-tolerant, incremental
- **Cons**: C bindings, setup complexity
- **Alternative considered**: Language-specific parsers (too many to maintain)

### 9.3 Chunking Strategy Decision

**Semantic over Fixed-size**:
- **Pros**: Preserves code logic, better retrieval
- **Cons**: Variable chunk sizes, complexity
- **Alternative considered**: Fixed 512-token chunks (loses context)

### 9.4 Why Not Just Full-Text Search?

RAG is necessary because:
- Semantic understanding (similar concepts, not just keywords)
- Handles paraphrased queries
- Scales to large codebases (10K+ files)
- Better ranking of relevance

---

## 10. Engineering Standards

### 10.1 Code Quality

**Followed**:
- ✅ Type hints (Python 3.11+, TypeScript strict mode)
- ✅ Linting (ruff, eslint)
- ✅ Formatting (black, prettier)
- ✅ Unit tests (pytest, vitest) - target 80% coverage
- ✅ Integration tests for API endpoints
- ✅ Pre-commit hooks (lint, format, test)

**Skipped** (time constraints):
- ⏭️ E2E tests (Playwright)
- ⏭️ Load testing (Locust)
- ⏭️ Security scanning (Snyk, Bandit)

### 10.2 Documentation

**Followed**:
- ✅ README with setup instructions
- ✅ API documentation (OpenAPI/Swagger)
- ✅ Architecture diagrams (this PRD)
- ✅ Inline docstrings (Google style)
- ✅ ADRs (Architecture Decision Records)

**Skipped**:
- ⏭️ Video walkthrough
- ⏭️ Postman collection

### 10.3 Version Control

**Followed**:
- ✅ Conventional commits
- ✅ Feature branches + PR reviews
- ✅ Protected main branch
- ✅ Semantic versioning (SemVer)

### 10.4 Security

**Followed**:
- ✅ Secret scanning in CI
- ✅ Environment variables for secrets
- ✅ HTTPS only in production
- ✅ Input validation (Pydantic)
- ✅ Rate limiting

**Skipped**:
- ⏭️ Penetration testing
- ⏭️ OAuth/SSO integration
- ⏭️ RBAC (Role-Based Access Control)

---

## 11. AI Tools Usage

### 11.1 Tools Used

1. **Claude (Anthropic)**:
   - Architecture planning
   - Code generation (boilerplate, utils)
   - Debugging assistance
   - Documentation writing

### 11.2 Best Practices

**DO's**:
- ✅ Use AI for boilerplate (Dockerfiles, configs)
- ✅ Generate test skeletons, then customize
- ✅ Ask AI to explain unfamiliar libraries
- ✅ Review and understand all AI-generated code
- ✅ Use AI for documentation first drafts

**DON'Ts**:
- ❌ Blindly accept complex algorithm implementations
- ❌ Skip reading AI-generated security-critical code
- ❌ Use AI outputs in README without verification
- ❌ Let AI make architectural decisions alone
- ❌ Copy-paste AI code without understanding

### 11.3 Repeatability Strategy

1. **Prompt Library**: Save effective prompts for future use
2. **Code Templates**: Extract AI-generated patterns into templates
3. **Review Checklist**: Standard checks for AI code
4. **Version Control**: Track AI-generated vs human-written code (Git blame)

### 11.4 Maintainability

- Add comments explaining AI-assisted sections
- Simplify AI-generated code for clarity
- Refactor overly complex AI suggestions
- Ensure AI code follows project conventions

---

## 12. Future Enhancements (With More Time)

### 12.1 Features

- [ ] **Multi-repo support**: Compare across codebases
- [ ] **Code change tracking**: Understand diffs and PRs
- [ ] **Interactive code editing**: Suggest code modifications
- [ ] **Codebase visualization**: Dependency graphs, call hierarchies
- [ ] **Automated documentation**: Generate README, docstrings
- [ ] **Test generation**: Create unit tests from code
- [ ] **Security analysis**: Vulnerability scanning
- [ ] **Performance insights**: Bottleneck detection

### 12.2 Technical Improvements

- [ ] **Hybrid cloud**: ChromaDB + Pinecone for scale
- [ ] **Caching layer**: Redis for frequent queries
- [ ] **Advanced chunking**: Graph-based code relationships
- [ ] **Multi-modal**: Include diagrams, screenshots
- [ ] **Fine-tuned embeddings**: Domain-specific code embeddings
- [ ] **Agentic workflows**: Multi-step reasoning (LangGraph)
- [ ] **Real-time updates**: Watch file system changes
- [ ] **Collaborative features**: Team annotations, shared knowledge

### 12.3 Production Readiness

- [ ] **Auto-scaling**: HPA (Horizontal Pod Autoscaling)
- [ ] **Multi-region deployment**: CDN for frontend
- [ ] **Disaster recovery**: Backup/restore for ChromaDB
- [ ] **Load balancing**: Nginx/Envoy ingress
- [ ] **Secrets management**: HashiCorp Vault
- [ ] **Observability**: Distributed tracing (Jaeger)
- [ ] **Cost optimization**: Spot instances, request batching
- [ ] **Compliance**: SOC2, GDPR considerations

---

## 13. Production Deployment Checklist

### 13.1 AWS Deployment

**Services Required**:
- **EKS** (Elastic Kubernetes Service): Container orchestration
- **RDS** (PostgreSQL): Temporal database
- **S3**: Uploaded codebase storage
- **EFS** (Elastic File System): ChromaDB persistent storage
- **ALB** (Application Load Balancer): Ingress
- **CloudWatch**: Logs and metrics
- **Secrets Manager**: API keys
- **ECR**: Container registry

**Estimated Monthly Cost** (for 1000 MAU):
- EKS cluster: $70 (control plane)
- EC2 instances (3x t3.large): $200
- RDS (db.t3.medium): $60
- S3 storage (100GB): $3
- EFS (50GB): $15
- Data transfer: $50
- **Total**: ~$400/month

**Scaling Strategy**:
- HPA on CPU/memory (target 70% utilization)
- EKS Cluster Autoscaler
- RDS read replicas for query load

### 13.2 GCP Deployment

**Services Required**:
- **GKE** (Google Kubernetes Engine)
- **Cloud SQL** (PostgreSQL)
- **Cloud Storage**: Codebases
- **Filestore**: ChromaDB volumes
- **Cloud Load Balancing**
- **Cloud Logging & Monitoring**
- **Secret Manager**

### 13.3 Azure Deployment

**Services Required**:
- **AKS** (Azure Kubernetes Service)
- **Azure Database for PostgreSQL**
- **Blob Storage**: Codebases
- **Azure Files**: ChromaDB volumes
- **Application Gateway**
- **Azure Monitor**
- **Key Vault**

### 13.4 Pre-Production Checklist

- [ ] Set up staging environment
- [ ] Load testing (1000 concurrent users)
- [ ] Failover testing
- [ ] Backup/restore validation
- [ ] Security audit
- [ ] Performance benchmarking
- [ ] Cost projection
- [ ] Monitoring dashboards configured
- [ ] Alerting rules set up
- [ ] Runbooks created
- [ ] Incident response plan
- [ ] On-call rotation established

---

## 14. Success Criteria

### 14.1 Functional Requirements ✅

- [x] Upload codebase (ZIP/GitHub URL)
- [x] Parse and chunk code semantically
- [x] Generate embeddings and index to vector store
- [x] Answer natural language queries
- [x] Cite sources with file paths and line numbers
- [x] Support multiple programming languages
- [x] Stream responses to UI
- [x] Handle large codebases (>1000 files)

### 14.2 Non-Functional Requirements ✅

- [x] **Performance**: Query response < 3s (p95)
- [x] **Scalability**: Handle 100 concurrent users
- [x] **Reliability**: 99% uptime
- [x] **Observability**: Metrics, logs, traces
- [x] **Maintainability**: Clean, tested, documented code
- [x] **Security**: Secrets management, input validation

### 14.3 Deliverables ✅

- [x] Working application (frontend + backend)
- [x] Comprehensive README
- [x] Architecture diagrams (HLD, LLD)
- [x] Deployment manifests (K8s, Docker Compose)
- [x] Tiltfile for local development
- [x] CI/CD pipelines
- [x] Test coverage > 70%
- [x] This PRD document

---

## 15. Timeline Estimate

**Phase 1 - Core Functionality (3-4 days)**:
- Day 1: Project setup, folder structure, Docker setup
- Day 2: Code parsing + chunking (Tree-sitter integration)
- Day 3: Embedding generation + ChromaDB indexing
- Day 4: Basic query pipeline (retrieval + LLM)

**Phase 2 - Frontend & API (2 days)**:
- Day 5: TanStack Start app, upload UI
- Day 6: Chat interface, streaming responses

**Phase 3 - Orchestration (2 days)**:
- Day 7: Temporal workflows for ingestion
- Day 8: LangGraph agent for query handling

**Phase 4 - Production Ready (2-3 days)**:
- Day 9: K8s manifests, Tiltfile
- Day 10: Observability (Prometheus, Grafana)
- Day 11: Testing, documentation, polish

**Total**: ~10-12 days for MVP

---

## 16. Appendix

### 16.1 Glossary

- **RAG**: Retrieval Augmented Generation
- **HLD**: High-Level Design
- **LLD**: Low-Level Design
- **AST**: Abstract Syntax Tree
- **CST**: Concrete Syntax Tree
- **BM25**: Best Matching 25 (sparse retrieval algorithm)
- **MRR**: Mean Reciprocal Rank (retrieval metric)
- **HPA**: Horizontal Pod Autoscaler

### 16.2 References

- Tree-sitter: https://tree-sitter.github.io/
- ChromaDB Docs: https://docs.trychroma.com/
- Temporal Docs: https://docs.temporal.io/
- LangGraph: https://langchain-ai.github.io/langgraph/
- TanStack Start: https://tanstack.com/start/

### 16.3 Sample Queries

1. "How does the authentication system work?"
2. "Where is the user login API endpoint implemented?"
3. "What are the dependencies of the payment module?"
4. "Show me all database models in this codebase"
5. "How is error handling done in the API layer?"
6. "What design patterns are used in this codebase?"

---

**END OF PRD**

---

**Quick Start Command**:
```bash
# Clone and setup
git clone <repo-url>
cd code-doc-assistant

# Start local development with Tilt
tilt up

# Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Temporal UI: http://localhost:8088
# Grafana: http://localhost:3001
```

This PRD should give you a complete blueprint for implementing the Code Documentation Assistant. Adjust scope based on your timeline!
# Infrastructure

Local development infrastructure for the Code Documentation Assistant.

## Services

The `docker/docker-compose.yml` file includes:

- **ChromaDB** (port 8000): Vector database for embeddings
- **Temporal** (ports 7233, 8233): Workflow orchestration with web UI at http://localhost:8233
- **PostgreSQL** (port 5432): Database for Temporal
- **Jaeger** (port 16686): Distributed tracing UI at http://localhost:16686
- **Prometheus** (port 9090): Metrics collection at http://localhost:9090
- **Grafana** (port 3000): Metrics visualization at http://localhost:3000 (admin/admin)

## Quick Start

### Using Docker Compose (recommended for local development)

```bash
cd infra/docker
docker-compose up -d
```

### Using Tilt

```bash
cd infra
tilt up
```

Tilt provides hot reload, log aggregation, and orchestration for all services.

## Environment Variables

Required environment variables (set in `.env` or export):

```bash
export ANTHROPIC_API_KEY=your_key_here
export JINA_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here  # Optional, for fallback embeddings
```

## Service URLs

Once running:

- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ChromaDB: http://localhost:8000
- Temporal UI: http://localhost:8233
- Jaeger UI: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Stopping Services

```bash
cd infra/docker
docker-compose down -v  # -v removes volumes
```

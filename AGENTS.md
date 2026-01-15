# Agent Guidelines for Code Documentation Assistant

This file contains build commands and code style guidelines for agentic coding assistants.

## Build, Lint, and Test Commands

### Backend (Python 3.12+)
```bash
cd backend

# Install dependencies and run tests
uv sync --all-extras
uv run pytest tests/                          # All tests
uv run pytest tests/unit/test_file.py::test_function_name  # Single test
uv run pytest tests/ --cov=app --cov-report=html  # With coverage

# Lint, format, and typecheck
uv run ruff check app/                       # Lint
uv run black app/                            # Format
uv run mypy app/                             # Type check
```

### Frontend (TanStack Start / React)
```bash
cd frontend

# Install dependencies and run tests
bun install
bun run test                          # All tests
bun run test -- path/to/test.test.tsx  # Single test
bun run test -- --watch               # Watch mode

# Lint, format, and typecheck
bun run lint                          # Lint
bun run format                        # Format
bun run typecheck                     # Type check
bun run build                         # Production build
```

### Infrastructure
```bash
# Local development
docker-compose -f infra/docker/docker-compose.yml up -d
tilt up                               # Recommended (infra/Tiltfile)

# Kubernetes deployment
kubectl apply -k infra/k8s/overlays/dev/
```

## Code Style Guidelines

### Python (Backend)

**Imports:** Use absolute imports (`from app.services import X`), group (stdlib → third-party → local), avoid wildcards.

**Formatting:** Black (88 chars), double quotes, trailing commas in multi-line lists.

**Type Hints:** Required on all functions. Use `Optional[T]` or `T | None` (3.11+). Return `None` explicitly.

**Naming:** Functions/vars: `snake_case`, Classes: `PascalCase`, Constants: `UPPER_SNAKE_CASE`, Private: `_prefix`.

**Error Handling:** Specific exceptions (`ValueError`, not `Exception`), custom exceptions in `app/core/exceptions.py`, log errors with context.

**Documentation:** Google-style docstrings, module-level docs, document public APIs.

**Async/Await:** Use `async def` for I/O, always `await`, use `asyncio.gather()` for concurrent ops.

**Testing:** pytest, unit tests in `tests/unit/`, mock external services, descriptive names: `test_parse_codebase_with_valid_file`.

### TypeScript/React (Frontend)

**Imports:** Absolute imports (`import from '@/components/ui/button'`), React → third-party → local.

**Components:** Function components, named exports (`export function X()`), TypeScript interfaces for props.

**Naming:** Components: `PascalCase`, Hooks: `useX`, Functions/vars: `camelCase`, Constants: `UPPER_SNAKE_CASE`.

**State:** TanStack Query for server state, React hooks for local, Context sparingly for app-wide.

**Error Handling:** Error boundaries, handle errors in `onError`, user-friendly messages, log to console.

**Styling:** Tailwind CSS utility classes, shadcn/ui components, avoid custom CSS.

**Testing:** Vitest + React Testing Library, mock with `vi.fn()`, focus on user interactions.

### General Guidelines

**File Organization:** Follow PRD structure, co-locate tests (`Component.tsx` + `Component.test.tsx`).

**API Design:** RESTful endpoints, appropriate HTTP codes, Pydantic validation, version endpoints `/api/v1/...`.

**Environment:** Use `.env.example`, never commit secrets, environment-specific configs.

**Git:** Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`), descriptive messages, small PRs.

**Security:** Validate input (Pydantic/Zod), sanitize output, HTTPS in production, no sensitive logs.

**Performance:** Async/await for I/O, caching, DB indexes, lazy loading, bundle optimization.

## Common Patterns

**Backend Service:**
```python
class CodeService:
    async def process_code(self, code: str) -> Result:
        try:
            result = await self._internal_process(code)
            logger.info("Success", extra={"result_id": result.id})
            return result
        except ProcessingError as e:
            logger.error(f"Failed: {e}")
            raise
```

**Frontend API Call:**
```typescript
export function useCodebases() {
  return useQuery({ queryKey: ['codebases'], queryFn: () => api.get('/api/v1/codebase') })
}
```

## When to Ask

Ask for clarification on: architectural decisions, breaking changes, performance vs maintainability trade-offs, security decisions, new major dependencies, non-trivial refactoring.

Never assume: external APIs not in PRD, UI/UX preferences, deployment specifics, budget/timeline, feature prioritization.

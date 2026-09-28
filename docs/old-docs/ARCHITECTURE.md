# Elevate Sprint — Architecture Guide

**Audience:** Sooraj's team (4 engineers), two-week evaluation sprint.
**Repo you work in:** `Strategiatech/elevate-sprint` (private scaffold). You never touch the main Strategia repos.
**Reviewer:** Minghao Qu reviews every PR.

This document tells you how the Strategia platform is shaped, which rules the shape enforces, and how the scaffold repo mirrors it so that what you build can be ported into the real codebase after the sprint. Read it once end-to-end, then keep section 2 and section 6 open while you code.

---

## 1. System at a glance

```
Browser
  │
  ▼
Next.js 15 static export (App Router, React 19, TypeScript, Tailwind)
  hosted on Azure Static Web Apps
  │  HTTPS, JSON, /api/* paths
  ▼
Azure Front Door / API Management (edge, routing, WAF)
  │
  ▼
ONE Python 3.11 Azure Functions app  ── a modular monolith
  │  hexagonal layout: routes → core/services → core/ports ← adapters
  ├── Azure SQL          (tenant data)
  ├── Azure Blob Storage (documents, templates)
  ├── Azure Service Bus  (async queues: email delivery, CV analysis, ...)
  └── Azure OpenAI       (structured LLM calls behind an AI port)
```

Facts you should internalise:

- **The frontend is a static export.** `next.config` sets `output: 'export'`. There are no Next.js server routes in production, no server components hitting a database, no `getServerSideProps`. Local development uses Next rewrites as a proxy to the Function App; the exported build calls the configured Function App origin directly. Browser code never talks to SQL.
- **One backend, many modules.** All HTTP routes, queue triggers and timers live in one Function App. Modules are separated by folder and by the hexagonal dependency rule, not by deployment unit.
- **Authorization is enforced server-side.** The frontend hides things for UX; the Function App middleware decides. Anything you gate only in React is not gated.
- **Multi-tenancy is domain-based and deployment-scoped.** Each deployed Function App is configured (via runtime settings) to serve one tenant database. The request does not choose the database: JWT claims, query parameters and headers that look like database selectors are ignored by the auth middleware. The tenant database name is put on the request context by middleware and threaded through every repository call as `database_name`. See section 6.
- **AI calls are structured.** Services call an `AIPort.call_structured(system_prompt, user_prompt, response_model: pydantic model, ...)` and get a typed model back. You will not see the production prompts; the scaffold gives you the port and a fake adapter.

[TODO Minghao: one-paragraph product brief for the Elevate module — what it does for which user role — goes here.]

---

## 2. The hexagonal rule set (backend)

The backend follows Ports & Adapters. The rules below are what the reviewer checks first. The docstring at the top of the production `JobService` states the rule exactly:

> The service NEVER imports from `services/`, `adapters/`, or `infrastructure/` directly — only from `core/ports/` and `ai/`.

### 2.1 Dependency direction

```
routes/  ──►  infrastructure/di/container.py  ──►  adapters/secondary/*
   │                                                     │ implements
   │ calls                                               ▼
   └────────►  core/services/*  ──►  core/ports/*  (ABCs)
                     │
                     └──►  core/domain/models/*  (pydantic), core/entities/*
```

- Dependencies point **inward**. `core/` imports nothing from `adapters/`, `infrastructure/`, `routes/`, `triggers/` or the legacy top-level `services/`.
- **Core has no Azure SDK imports.** No `azure.*`, `pyodbc`, `openai`, `requests` inside `core/`. If you need I/O, define a port.
- Adapters and infrastructure import from core. Never the reverse.
- `ai/` is treated as core business logic (allowed import from services). In the scaffold you will not have production `ai/` modules; use the AI port.

### 2.2 Layer by layer

| Layer | Path | What goes here | What must not go here |
|---|---|---|---|
| Ports | `core/ports/<thing>_port.py` | One `ABC` per external capability, `@abstractmethod` on every operation, type-hinted signatures, docstrings describing the contract (e.g. `RepositoryPort`, `AIPort`, `StoragePort`, `EmailPort`, `AuthPort`) | Any implementation, any SDK import |
| Domain models | `core/domain/models/*.py` | Pydantic request/response models, enums, validators | I/O |
| Use cases | `core/services/<thing>_service.py` | A class per bounded use-case set. Constructor takes ports (`__init__(self, repository: RepositoryPort, ai: AIPort)`). Public methods are the use cases. Pure orchestration and business rules. | SDK imports, `os.environ` reads, HTTP objects (`func.HttpRequest`), imports from `adapters/`, `infrastructure/`, top-level `services/` |
| Adapters | `adapters/secondary/azure_<tech>_adapter.py` and `<domain>_sql_repository.py` | Concrete implementations of a port using one technology (`AzureSqlAdapter`, `AzureBlobAdapter`, `AzureOpenAIAdapter`, `AzureEmailAdapter`, `AzureAuthAdapter`) | Business rules, decisions that belong to a service |
| Composition root | `infrastructure/di/container.py` | Plain factory functions: `get_job_service()` builds `JobService(repository=AzureSqlAdapter(), ai=AzureOpenAIAdapter())`. **No DI framework**, no decorators, no registry classes. Service imports are done inside the factory function to avoid import cycles. Environment variables are read here (production also has `infrastructure/runtime_settings.py`), never in core. | Business logic |
| HTTP infrastructure | `infrastructure/http/` | `compose_middleware`, middleware modules, `json_response`, request context | Business logic |
| Routes | `routes/<thing>_routes.py` | `register_<thing>_routes(app)` containing `@app.route(...)` handlers. **Thin adapters: parse → delegate → respond.** | SQL, business rules, direct adapter construction |
| Registry | `function_app.py` | Creates the `FunctionApp`, resolves host-level settings from environment, calls each `register_*_routes(app)` and registers triggers. | Anything else |

### 2.3 Route shape and middleware order

Every authenticated route is composed like this, and the order matters (first listed = outermost):

```python
@app.route(route="elevate/items", methods=["POST"])
@compose_middleware(
    error_middleware,          # 1. catches everything, returns a consistent error body
    logging_middleware,        # 2. correlation id, timing, no PII
    auth_middleware,           # 3. JWT → context.user, context.database_name
    require_permission("elevate:write"),   # 4. role/permission check
    validate_body(CreateElevateItemRequest),  # 5. pydantic parse → context.body
)
def create_elevate_item_handler(req, context):
    result = get_elevate_service().create_item(
        payload=context.body,
        user_id=context.user_id,
        database_name=context.database_name,
    )
    return json_response({"success": True, "data": result}, status_code=201)
```

That is the production shape. The scaffold does not ship the middleware stack: its handlers in `routes/goal_routes.py` validate the body with a pydantic model, map domain errors to `error_response(...)` explicitly, and read the tenant from a header. When Strategia ports your work, the `try/except` blocks disappear and the middleware takes over, so keep handlers thin enough for that to be a mechanical change.

Rules:

- `error → logging → auth → require_permission → validate_body`. Do not reorder. Do not skip `error_middleware`.
- The handler reads from `context`, calls one service factory, returns `json_response`. No `try/except` for business errors in the handler (error middleware maps domain errors to HTTP). No SQL, no `os.environ`, no adapter construction.
- Permission names and feature flags are checked here, not inside services. Services trust that the caller was authorised; they still scope every query by tenant.
- Response envelope: `{"success": bool, "data": ...}` on success; error middleware owns the error envelope. Keep it — the frontend helpers depend on `error`, `code`, and the correlation id.

### 2.4 The naming collision — read this twice

The production backend has **two** folders called `services`:

| Path | What it is | Do you add code here? |
|---|---|---|
| `services/` (top level) | **Legacy technical modules**: `sql_database.py`, `blob_storage.py`, `email_service.py`, `auth_service.py`, `openai_usage_service.py`, SSO helpers. These predate the hexagonal refactor and are now wrapped by adapters. | **No.** |
| `core/services/` | **Domain use cases**: `job_service.py`, `candidate_service.py`, `assessment_service.py`, `ats_service.py`, ... | **Yes.** All new domain logic goes here. |

Likewise there is a legacy top-level `middleware/auth_middleware.py` (the old `@require_auth` decorator) and the current `infrastructure/http/middleware/`. Use the latter. The older `docs/ARCHITECTURE_SUMMARY.md` in the main repo describes the pre-refactor layout (`ai/` + `services/`); treat the layout in this document as current.

The scaffold repo does not contain the legacy folders, so you cannot make this mistake there — but your Day-3 recommendation and your PR descriptions must use the right names.

---

## 3. Frontend mirror

The frontend is organised by business feature, with the same "dependencies point inward, I/O at the edge" idea.

### 3.1 Layout

```
src/
├── app/                      # Next.js App Router: route wrappers, layouts, metadata, page composition only
├── core/
│   ├── entities/             # shared domain values, enums, domain errors (per domain folder)
│   ├── models/               # service DTOs and validation schemas
│   └── ports/                # contracts still referenced by app code / OpenAPI tooling
├── features/<feature>/
│   ├── api/                  # THE ONLY place that calls the backend for this feature (typed URL builders + fetchers)
│   ├── components/           # feature UI, colocated *.test.tsx
│   ├── constants/            # query keys, feature constants
│   ├── hooks/                # React hooks composing api/ calls for components
│   ├── types/                # request/response contracts
│   ├── utils/                # pure transformations, colocated *.test.ts
│   ├── index.ts              # public API of the feature
│   └── README.md             # what the feature owns, hooks, data flow
├── components/ui/            # thin adapters over @strategiatech/design-system primitives
├── lib/                      # cross-feature infrastructure: api transport, auth, errors, openapi, styles (tokens)
└── shared/                   # deliberate cross-feature components/utilities
```

Notes from the real repo:

- There is **no** `src/core/services` on the frontend and there will not be one. Business operations are implemented by the Function App. `src/core/README.md` says it plainly: do not create empty services or adapters merely to match an architecture diagram.
- `src/core/ports` is listed in the core README but the current `platform` checkout only contains `core/entities` and `core/models`. The scaffold does ship `src/core/ports/goalRepositoryPort.ts`: it is the contract the feature's `api/` module implements and the fake that component tests inject. Keep that shape for Elevate.

### 3.2 Import rules

```ts
// allowed: a feature's public API
import { useGoals } from '@/features/elevate'
import type { Goal } from '@/features/elevate'

// forbidden: reaching into another feature's internals
import { ItemCard } from '@/features/elevate/components/ItemCard'
```

- `app/` pages import from feature `index.ts` files and compose them. Pages do not fetch.
- Feature components use feature hooks; hooks use the feature `api/` module; `api/` uses `lib` transport. Nothing skips a layer.
- No direct `fetch` outside `features/<x>/api`. Never patch `window.fetch`. Native `fetch` is reserved for reviewed external transport (e.g. signed storage uploads).
- Plain API functions are not named `useSomething`. Hooks are.
- Shared UI primitives come from `src/components/ui` (thin wrappers over the design system: `button.tsx`, `dialog.tsx`, `select.tsx`, `table.tsx`, ...). Do not fork a primitive into a feature; do not add feature business logic (e.g. candidate email flows) to `components/ui`.
- Styling uses Tailwind plus design tokens from `@strategiatech/design-system` and `src/lib/styles` (e.g. ATS colours, chart colours, metric-state tokens). No hard-coded hex colours in feature code.

### 3.3 Two API access paths (and a third file you will see)

| Module | Use it for | Behaviour |
|---|---|---|
| `src/lib/auth/authFetch.ts` → `authFetch()` | **All authenticated application calls.** This is the default. | Wraps `authenticatedFetch`: attaches the session, handles token refresh, bounded transient retries. Returns a `Response`. |
| `src/lib/api/apiFetch.ts` → `apiFetch()` | Deliberately public/discovery calls (e.g. client settings before login) and best-effort telemetry that must **not** trigger an auth refresh. | Rewrites `/api/*` to the configured backend origin in exported builds, keeps Next rewrites locally. Returns a `Response`, does not parse JSON, never refreshes auth. |
| `src/lib/directApi.ts` | Not a transport. Normalisers for the established `*_direct` list endpoints (`normalizeDirectListResponse`, calendar envelope). | Accepts either a bare array or `{ data, success, executionTime, recordCount, ... }` and returns one stable envelope. |

Rule of thumb for Elevate: the scaffold has a single transport, `apiFetch` in `src/lib/api.ts`, which throws `ApiError(status, code, message)`. `features/elevate/api/goalsApi.ts` is the only module that calls it; it maps the backend's snake_case DTOs to the camelCase `Goal` entity and returns typed results. When the work is ported into the platform, `apiFetch` calls become `authFetch` calls; nothing else in the feature should need to change.

---

## 4. How the scaffold repo mirrors this

```
elevate-sprint/
├── backend/
│   ├── function_app.py                          # thin registry: create FunctionApp, register blueprints
│   ├── routes/goal_routes.py                    # HTTP adapter (func.Blueprint), thin handlers
│   ├── core/
│   │   ├── domain/elevate.py                    # Goal dataclass + domain errors, pure Python
│   │   ├── ports/goal_repository_port.py        # ABC, database_name keyword-only on every method
│   │   ├── ports/ai_port.py                     # ABC, same shape as the production AI port
│   │   └── services/goal_service.py             # use cases
│   ├── adapters/secondary/
│   │   ├── in_memory_goal_repository.py         # complete; tests and local dev
│   │   ├── azure_sql_goal_repository.py         # STUB: correct signatures, raises NotImplementedError
│   │   └── fake_ai_adapter.py                   # deterministic canned text, records calls
│   ├── infrastructure/
│   │   ├── di/container.py                      # get_goal_service() and friends; the only os.environ reads
│   │   └── http/responses.py                    # json_response / error_response envelope
│   ├── tests/
│   │   ├── test_goal_service.py
│   │   ├── test_goal_routes.py
│   │   └── test_adapter_substitutability.py
│   ├── pyproject.toml                           # ruff + mypy (strict) + pytest config
│   ├── requirements.txt  requirements-dev.txt  host.json  local.settings.example.json
└── frontend/
    ├── src/app/{layout,page}.tsx                # App Router; page composes the feature
    ├── src/core/entities/goal/                  # Goal type + validation, framework-free
    ├── src/core/ports/goalRepositoryPort.ts     # contract implemented by features/elevate/api
    ├── src/features/elevate/{api,components,constants,hooks,types,utils,index.ts,README.md}
    ├── src/lib/api.ts                           # apiFetch: the single HTTP entry point
    ├── src/components/ui/                       # keep any reusable primitive here, with a test
    └── jest.config.ts  eslint.config.mjs  .prettierrc  tsconfig.json  next.config.ts
```

CI (`.github/workflows/ci.yml`) runs on every PR: backend `ruff check`, `ruff format --check`, `mypy`, `pytest`; frontend `eslint`, `tsc`, `prettier --check`, `jest`, `next build`; plus a secret scan. All of it must be green before you request review.

### 4.1 The reference example — a `Goal` entity

The scaffold ships one complete, deliberately boring vertical slice. Extend it; do not restructure it.

1. **Domain** — `core/domain/elevate.py`. `Goal` is a plain dataclass that validates its own invariants in `__post_init__` (title required, 200 chars max). Domain errors (`GoalNotFoundError`, `ValidationError`) live next to it. No pydantic here; pydantic belongs at the HTTP boundary.

2. **Port** — `core/ports/goal_repository_port.py`

   ```python
   class GoalRepositoryPort(ABC):
       @abstractmethod
       def add(self, goal: Goal, *, database_name: str) -> Goal: ...
       @abstractmethod
       def get(self, goal_id: str, *, database_name: str) -> Goal | None: ...
       @abstractmethod
       def list_for_employee(self, employee_id: str, *, database_name: str) -> list[Goal]: ...
       @abstractmethod
       def update(self, goal: Goal, *, database_name: str) -> Goal: ...
   ```

   Every method takes `database_name` keyword-only. That is the tenancy contract (section 5.1); a repository method without it will be rejected in review.

3. **In-memory adapter** — `adapters/secondary/in_memory_goal_repository.py`. A dict keyed by `(database_name, goal_id)`. Complete, deterministic, used by unit tests and local runs.

4. **Azure SQL adapter stub** — `adapters/secondary/azure_sql_goal_repository.py`. Same port, correct signatures, every method raises `NotImplementedError`. Implementing it against the synthetic dev database is a sprint task: parameterised SQL only, one connection per tenant database, rows mapped to `Goal` and back, no business rules. Define the table in a new `backend/sql/` folder; table names are not shared with production. Wire it in `container.py` under `GOAL_REPOSITORY=sql` and add it to `REPOSITORY_FACTORIES` in the substitutability test (skip when no connection is configured).

5. **AI port and fake adapter** — `core/ports/ai_port.py` (`generate(instruction, context) -> str`) and `adapters/secondary/fake_ai_adapter.py`. `GoalService.suggest_description` shows a use case crossing the AI port without persisting anything. The production Azure OpenAI adapter and its prompts are not part of the scaffold.

6. **Service** — `core/services/goal_service.py`. `GoalService(repository, ai)`. Use cases as public methods, all taking `database_name` keyword-only. Raises domain errors; never returns HTTP codes.

7. **Container** — `infrastructure/di/container.py`. `get_goal_repository()` (`GOAL_REPOSITORY=memory|sql`), `get_ai_adapter()` (`AI_ADAPTER=fake`), `get_goal_service()`. This is the only place that knows which adapter is live and the only place that reads `os.environ` for wiring.

8. **Route** — `routes/goal_routes.py`. Pydantic body models, thin handlers: parse → delegate → `json_response` / `error_response`. In the scaffold the tenant database comes from the `x-tenant` header so routes are testable locally; in production it is injected by the auth middleware from the JWT. Do not ship the header approach.

9. **Tests**
   - `tests/test_goal_service.py`: service with the in-memory repository and fake AI adapter. Fast, offline, covers business rules and tenant scoping.
   - `tests/test_goal_routes.py`: handlers called directly with a `func.HttpRequest`; asserts status codes and the error envelope.
   - `tests/test_adapter_substitutability.py`: structural check (every adapter in `ADAPTER_PORT_PAIRS` subclasses its port, implements every abstract method, keeps the port's parameter names) plus a behavioural round-trip for every factory in `REPOSITORY_FACTORIES`. Add your pairs; when the test fails, fix the adapter, not the test.

10. **Frontend slice** — `src/core/entities/goal/goal.entity.ts` (type + `validateGoalTitle`), `src/core/ports/goalRepositoryPort.ts`, `features/elevate/api/goalsApi.ts` (the only `apiFetch` calls, snake_case DTO → camelCase entity mapping), `hooks/useGoals.ts` (accepts a repository so tests inject a fake), `components/GoalList.tsx` + `GoalList.test.tsx`, `utils/formatGoalStatus.ts` + test, `constants/`, `types/`, `index.ts`, `README.md`.

### 4.2 Adding a new capability (checklist)

1. Entity or field in `core/domain/`, with its invariants and a unit test.
2. If it needs new I/O: port in `core/ports/`, in-memory adapter, SQL adapter (stub or real), add the pair to `ADAPTER_PORT_PAIRS`.
3. Use case method on the service, with tests against the in-memory adapter.
4. Factory update in `container.py` if a constructor changed.
5. Route handler (pydantic body model, thin handler) and a route test.
6. Frontend: `api` function → hook → component → page, with colocated tests.
7. Feature README updated.

---

## 5. Cross-cutting rules

### 5.1 Tenancy boundary

- Tenant identity comes from runtime configuration (the deployment's configured database) via middleware → `context.database_name`. Never from a request parameter, header, or JWT claim that names a database.
- **Every repository method takes `database_name` and every query is scoped by it.** No "list all" without a tenant. No cross-tenant joins.
- Services receive `database_name` from the route and pass it through unchanged. They do not default it, cache it, or read it from the environment.
- `organization_id` may be stored as metadata on rows for future shared-runtime models, but it is not the isolation control today. [TODO Minghao: confirm whether Elevate rows should carry `organization_id` from day one.]
- Roles you will see: `manager`, `recruiter`, `candidate`, `admin`, `support`, `service`. Sensitive routes can disable the default admin bypass with `allow_admin_bypass=False`. Decide the role/permission per Elevate route explicitly in the PR description.

### 5.2 No PII in logs

- Logs must never contain: candidate name, candidate email, resume filename, raw resume/transcript text, prompt text, model response bodies, tokens, full SAS/download URLs.
- Log stable hashes or presence booleans instead (`has_attachment=True`, `item_ref=<sha256 prefix>`).
- Every request has a correlation id (`X-Correlation-ID`, falling back to `X-Request-ID`, then a generated UUID). Logging middleware sets it; queue messages carry it; responses return it. Include it, and only it, when you log something about a request.
- Same rule in the browser: do not `console.log` resumes, transcripts, tokens or signed URLs.

### 5.3 Configuration via environment only

- All settings are read from environment variables inside a container factory (`infrastructure/di/container.py`; production also has `runtime_settings.py`). Core code never reads `os.environ`.
- Local development uses `local.settings.json` (git-ignored) for the backend and `.env.local` (git-ignored) for the frontend. Commit `*.example` files with placeholder values.
- Production secrets live in Azure Key Vault and are surfaced as app settings; you will not have access to any of them.

### 5.4 No secrets in code

- No connection strings, API keys, JWT secrets, storage keys or tokens in source, tests, fixtures, commit messages, PR descriptions or chat. CI runs a secret scan; a hit fails the build and the PR is closed.
- Test fixtures use obviously fake values (`"sk-test-not-real"`, `"Server=localhost;Database=elevate_test"`).

---

## 6. What you do not get, and where your code goes

You do **not** receive:

- The production `platform`, `function-app-backend`, `Interview-Platform` or `strategia-infra` repositories, or read access to them.
- Production prompts, the `ai/` modules, scoring or classification logic, competency models, psychometric configuration.
- Real data of any kind: no customer databases, no exports, no screenshots, no recordings, no test accounts on staging or production. Synthetic data only (see CODING_PRINCIPLES.md section 7).
- Azure subscriptions, Key Vault contents, connection strings, or deployment pipelines.

Your PRs merge into `Strategiatech/elevate-sprint` only. After the sprint, Strategia decides which accepted work to port into the main repositories and does the port itself — this is why matching the layout, naming and rules in this document matters: code that fits the shape ports in hours, code that does not gets rewritten or dropped.

---

## Appendix A — Quick reference

| Question | Answer |
|---|---|
| Where does business logic go? | `backend/core/services/` |
| Where do I talk to SQL/Blob/OpenAI? | An adapter in `backend/adapters/secondary/`, behind a port in `backend/core/ports/` |
| Where do I read config? | a `container.py` factory |
| Where do I wire things? | `infrastructure/di/container.py`, plain functions |
| What does a route do? | parse → delegate → respond, with `error → logging → auth → require_permission → validate_body` |
| Where does the frontend call the API? | `features/elevate/api/` via `apiFetch` (`authFetch` in production) |
| Where do shared UI primitives live? | `src/components/ui`, wrapping `@strategiatech/design-system` |
| Which `services/` folder? | `core/services/`. The top-level one is legacy. |
| What must every query have? | `database_name` from the request context |

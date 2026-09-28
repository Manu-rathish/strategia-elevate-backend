# Elevate Sprint — Coding Principles and Working Agreement

**Audience:** Sooraj's team, two-week evaluation sprint in `Strategiatech/elevate-sprint`.
**Companion:** ARCHITECTURE.md (read it first).
**Reviewer:** Minghao Qu.

These are the rules a PR is reviewed against. They are short on purpose. If a rule is unclear, ask in the Teams channel before you build on your interpretation.

---

## 1. Principles

1. **Small PRs.** Under 400 changed lines (excluding lock files and generated code). If it is bigger, split it. A large PR waits longer and gets a shallower review.
2. **One concern per PR.** A feature, a fix, or a refactor — not two of them. Do not mix formatting-only changes with logic changes.
3. **Tests with every change.** Changed logic ships with tests in the same PR. A PR without tests for changed logic needs an explicit justification in the description; "will add later" is not one.
4. **Thin handlers.** Route handlers and React pages parse, delegate and render. No business rules in them.
5. **No cross-layer imports.** Backend `core/` never imports `adapters/`, `infrastructure/`, `routes/`. Frontend features never import another feature's internals; nothing but `features/<x>/api` calls the backend. CI enforces the backend rule with an import-boundary test; the reviewer enforces the rest.
6. **Explicit types.** Type hints on every public Python function; `strict` TypeScript with no `any` outside a justified, commented boundary.
7. **No dead code.** No commented-out blocks, unused exports, `TODO` without an owner, or compatibility shims without a concrete consumer and a removal plan. Delete what you replace.
8. **English identifiers and comments.** Code, comments, commit messages, PR text: English only.
9. **Minimal complete change.** Do what the ticket needs, reuse existing patterns, and include the callers, types and contracts your change affects. Do not restructure the scaffold to match a preference.
10. **Do not weaken guards to make tests pass.** Authentication, validation, tenancy scoping, audit and rate-limiting are never loosened to get green. If a test needs it, the test is wrong.
11. **Read before you change.** Open the callers, the types, the tests and the config for the code you are touching. Do not grep the whole repo and patch the first match.
12. **Say what you verified.** In PR descriptions and end-of-day updates, separate "tests pass" from "I ran it and saw X". CI green is not acceptance.

---

## 2. Python standards (backend)

| Item | Rule |
|---|---|
| Version | Python 3.11. Do not use 3.12-only syntax. |
| Lint + format | `ruff check .` and `ruff format --check .` run in CI. Config lives in `backend/pyproject.toml` (`[tool.ruff]`). Run `ruff format` before you commit. |
| Types | `mypy --strict` runs in CI against `backend/` (config in `pyproject.toml`). Type hints on all public functions and methods (arguments and return). `Any` needs a comment. |
| Boundary models | Request bodies are pydantic models declared next to the route (`CreateGoalBody` in `routes/goal_routes.py`) and validated with `model_validate`; handlers never read raw dicts. Domain objects are plain dataclasses in `core/domain/`. Services accept domain objects or primitives, never `func.HttpRequest`. |
| Ports | `ABC` + `@abstractmethod`, one port per capability, keyword-only `database_name` on every repository method. |
| Errors | Services raise domain errors (`core/domain/elevate.py`). Routes map them to `error_response(code, message, status)`. No `except Exception: pass`. |
| Logging | `logging.getLogger(__name__)`. Structured fields, correlation id from context, no PII (see ARCHITECTURE.md 5.2). No `print`. |
| Config | `os.environ` only in `infrastructure/di/container.py`. |
| Imports | Absolute imports from the `backend/` root. Service imports inside container factories are allowed to avoid cycles. |
| Tests | `pytest`. Files named `tests/test_<module>.py` mirroring the module under test (`core/services/goal_service.py` → `tests/test_goal_service.py`). Test functions named `test_<behaviour>` describing the observable behaviour, not the implementation. Fixtures in `tests/conftest.py`. |
| Test doubles | Use the in-memory adapters and the fake AI adapter from the scaffold. Mock only at a port boundary. Never hit Azure in a unit test. |
| Regression tests | When fixing a bug, first write the test that fails on the old behaviour, then fix. |

**Adapter substitutability pattern.** Every adapter/port pair is registered in `tests/test_adapter_substitutability.py`:

```python
ADAPTER_PORT_PAIRS = [
    (InMemoryGoalRepository, GoalRepositoryPort),
    (AzureSqlGoalRepository, GoalRepositoryPort),
    (FakeAIAdapter, AIPort),
]
```

The test asserts, for each pair, that the adapter subclasses the port, implements every abstract method, and keeps the port's parameter names. Working repository adapters are also run through a behavioural round-trip via `REPOSITORY_FACTORIES`. When you add an adapter, add the pair. When the pair test fails, fix the adapter, not the test.

Commands (from `backend/`):

```
ruff check . && ruff format --check . && mypy . && pytest
```

The same four commands run in CI (`.github/workflows/ci.yml`).

---

## 3. TypeScript standards (frontend)

| Item | Rule |
|---|---|
| Language | TypeScript 5, `"strict": true` in `tsconfig.json`. `npx tsc --noEmit` runs in CI. |
| Framework | Next.js 15 App Router, React 19, static export (`output: 'export'`). No server actions, no API routes, no `getServerSideProps`. |
| Lint | ESLint flat config extending `next/core-web-vitals` and `next/typescript`. Zero warnings policy in CI. |
| Format | Prettier: `semi: false`, `singleQuote: true`, `tabWidth: 2`, `trailingComma: 'es5'`, `prettier-plugin-tailwindcss`. Run on save or before commit. |
| Styling | Tailwind 4 + `@strategiatech/design-system` tokens. No hard-coded colours; no inline style objects for things tokens cover. |
| Layout | Feature slice: `features/elevate/{api,components,constants,hooks,types,utils,index.ts,README.md}`. Public API only through `index.ts`. |
| Requests | Only `features/<x>/api/*.ts` calls the backend, via `apiFetch` from `@/lib/api` (`authFetch` in production). No `fetch` elsewhere. Never patch `window.fetch`. |
| Errors | Preserve status, code and correlation id through `src/lib/api/errors.ts` helpers. Keep user-visible messages stable during refactors. |
| Hooks vs functions | Only React hooks are named `useX`. API functions are plain verbs (`goalsApi.listForEmployee`). |
| State | The scaffold uses plain hooks (`useGoals`) that take the repository as a parameter so tests can inject a fake. If you add TanStack Query, keep query keys in `features/elevate/constants/`. Component state for UI only. |
| Tests | Jest + `@testing-library/react`, colocated: `Component.tsx` → `Component.test.tsx`, `useX.ts` → `useX.test.tsx`, `helpers.ts` → `helpers.test.ts`. Inject a fake `GoalRepositoryPort` (see `GoalList.test.tsx`) instead of mocking `fetch`. |
| Test tiers | Unit (pure utils, isolated components) is the bulk; integration (hooks with msw, feature boundaries) is the middle; E2E is out of scope for the sprint. Test behaviour and contracts, not implementation details. |
| Accessibility | Interactive elements need accessible names. Use the `components/ui` primitives which keep Radix focus handling. |

Commands (from `frontend/`):

```
npm run lint && npx tsc --noEmit && npm test -- --ci && npm run build
```

---

## 4. Git workflow

- **Base branch:** `main` of `Strategiatech/elevate-sprint`. Branch from an up-to-date `main`.
- **Branch names:** `feat/elevate-<short>`, `fix/elevate-<short>`, `chore/elevate-<short>`, `docs/elevate-<short>`. Lower-case, hyphens, under 40 characters after the prefix.
- **Commits:** Conventional Commits. `feat(backend): add elevate item listing`, `fix(frontend): keep query key stable on refetch`, `test(backend): cover empty tenant list`. Subject under 72 characters, imperative mood, body explains why when it is not obvious. One logical change per commit; squash local fix-ups before opening the PR.
- **PR template:** every field filled — problem, change, how it was tested (commands run, what you observed), screenshots of synthetic data only if UI changed, checklist ticked honestly. Unfilled template = PR sent back without review.
- **CI green before review.** Do not request review on a red build. Do not `@`-mention the reviewer to skip the queue.
- **Review SLA:** Minghao reviews within one working day (IST overlap window). If a PR waits longer, post in the channel; do not open a duplicate.
- **Addressing comments:** push **new commits**; never force-push or rebase once review has started. Reply to each comment (a link to the commit is enough). Re-request review when all comments are addressed.
- **Merge:** squash merge by the reviewer. The squash title becomes the changelog line, so keep the PR title a valid conventional commit.
- **Do not:** commit directly to `main`, merge your own PR, merge another team member's PR, disable a CI check, or add `[skip ci]`.
- **Keep the branch small and short-lived.** If a branch is older than three working days, split or finish it.

---

## 5. Definition of Done (sprint version)

Adapted from the Strategia SDLC. A change is Done when all of the following hold:

1. The acceptance criteria written on the issue are met and the PR description says how each was verified.
2. Tests are written with the change and green in CI; coverage did not decrease.
3. `ruff`, `mypy`, ESLint, `tsc` and Prettier are clean.
4. No cross-layer import, no PII in logs, no secret in code — checked by CI and by the reviewer.
5. Feature README (frontend) and any touched docs are updated. Docs describe what exists, not what is planned.
6. The reviewer ran the change locally (or a synthetic-data walkthrough was provided) and accepted it.
7. Squash-merged into `main` of the scaffold repo and the issue is closed with a link to the PR.

Not part of Done for this sprint: deployment to a Strategia environment, staging QA, release tagging. Strategia does those after porting.

---

## 6. Daily rhythm

- **Stand-up:** a 15-minute call on Teams, inside the 09:00–13:00 IST overlap window. [TODO Minghao: fix the exact time.] Each engineer: what merged yesterday, what is in review, what is blocked. Blockers get an owner before the call ends.
- **Written end-of-day update:** one message per engineer in the Teams channel before you log off, format:

  ```
  Done: PR #12 merged (elevate item list), PR #14 in review
  Verified: pytest + jest green; walked through list → detail with synthetic data
  Next: pagination on list endpoint
  Blocked: need decision on role for elevate:write (asked in thread)
  ```

- **Questions:** ask in the channel thread, not in DMs, so answers are visible to all four engineers. Tag Minghao only for decisions.
- **Decisions are written down** in the issue or PR they affect, not only in chat.

---

## 7. Security and confidentiality (from the NDA)

These are contractual obligations, not preferences. Breaching one ends the engagement.

1. **Synthetic data only.** All fixtures, seeds, screenshots and demos use invented data (names like "Test Candidate 01", emails on `example.com`). Never paste, type or upload real personal data into the repo, the scaffold environment, tickets, chat or any tool.
2. **No screenshots, recordings or exports from the Strategia platform.** You do not have platform access; if you are ever shown it in a call, do not capture it.
3. **AI coding tools:** no tool that retains or trains on your input may be used on this code unless approved in writing by Strategia. **Approved tools: none yet — ask before using any**, including IDE assistants, chat models and code-completion plugins. If approved later, the approval will name the tool, the account type and the data-retention setting.
4. **No secrets in code or chat.** No keys, tokens, connection strings or passwords anywhere: not in source, fixtures, `.env` committed by mistake, PR text, Teams or screenshots. If you receive one, do not store it; tell Minghao.
5. **Report anything that looks like real personal data immediately** — in a fixture, a sample file, a log, a ticket. Do not delete it yourself, do not forward it; message Minghao directly with the location.
6. **Access is personal.** Do not share repo access, tokens or accounts with anyone, including other members of your team.
7. **Nothing leaves the scaffold repo.** No copying code or docs to personal machines, personal repos, gists, or other clients' projects, during or after the sprint.

---

## 8. Day-3 architecture recommendation — and how to flag optimisation opportunities

By the end of Day 3, the team submits **one page** (as `docs/day3-recommendation.md` in a PR) using this exact structure. Use the same format, one page each, for any "backend optimisation opportunity" you want to flag at any point in the sprint (`docs/opportunities/<short>.md`).

```
# <Title — one line>

## Problem
What is wrong or limiting today, in one paragraph. Name the file/layer.
Not "the architecture could be better" — a specific pain you hit.

## Evidence
What you observed: test output, a measured number, a concrete code path,
a reproduction. No evidence, no recommendation.

## Proposed change
What you would change, where, and what it would look like after.
Which rule in ARCHITECTURE.md it keeps or needs to change.

## Risk
What could break, who is affected, how it would be rolled back.

## Effort
S / M / L with a sentence of justification and the PR split you would use.
```

Ground rules for recommendations:

- Facts about the platform beyond what the scaffold and these two documents show are unknown to you — say so rather than assume. A recommendation that depends on production internals should list the question you need answered.
- Prefer changes that fit the existing shape over changes to the shape.
- One recommendation per page; three good pages beat one long one.
- Minghao replies in writing with accept / defer / decline and the reason.

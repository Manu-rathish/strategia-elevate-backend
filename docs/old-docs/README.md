# Elevate — sprint scaffold

Private scaffold repository for the two-week Elevate evaluation sprint. This is the **only**
repository the sprint team works in. It mirrors the layout, tooling and rules of the Strategia
platform so that accepted work can be ported into the main repositories by Strategia after the
sprint.

Confidential. Covered by the Sprint Confidentiality & IP Agreement each contributor has signed.

## Start here

1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the platform is built and the rules every
   change must follow.
2. [docs/CODING_PRINCIPLES.md](docs/CODING_PRINCIPLES.md) — code standards, git workflow,
   Definition of Done, confidentiality rules.
3. [docs/FEATURE_WALKTHROUGH.md](docs/FEATURE_WALKTHROUGH.md) — a contractor-safe map of the
   current Job and assessment flows, with a shared synthetic demo plan and example prompt patterns.
4. [docs/PROMPT_PATTERNS.md](docs/PROMPT_PATTERNS.md) — source-mapped example prompts for CV Analyze,
   V-Scenario, V-Interview and V-Psych using fictional development data.
5. The Sprint Brief, Requirements Specification and Screen Playbook you received from Gaurav
   (not stored in this repo).

## Layout

```
backend/    Python 3.11 Azure Functions — hexagonal (core / adapters / infrastructure / routes)
frontend/   Next.js 15 static export — feature slices (src/features/<feature>) over src/core
docs/       architecture, coding principles, feature walkthrough and prompt patterns
.github/    CI (ruff, mypy, pytest, eslint, tsc, prettier, jest, build, secret scan), PR template
```

Both halves ship with a small worked example — a `Goal` entity — wired end to end
(port → adapter → service → container → route → tests, and entity → port → api → hook →
component → tests). Extend it; do not bypass it.

## Local setup

Backend:

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && mypy . && pytest
cp local.settings.example.json local.settings.json   # then: func start
```

Frontend:

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run validate     # lint + typecheck + prettier + jest
npm run dev
```

## Workflow

- Branch from `main`: `feat/elevate-<short-name>`, `fix/<short-name>`.
- Small PRs (about 400 lines max), template filled in, CI green, then request review.
- Minghao Qu reviews every PR (CODEOWNERS). Squash merge only.
- Daily stand-up in the 9:00–13:00 IST window on Teams; written end-of-day update.

## What is not here, on purpose

Production code, prompts, scoring logic, real or client data, environment configuration and
secrets. If you think you need any of them, ask in the stand-up.

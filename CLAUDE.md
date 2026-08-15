# SGW Resilience Platform

An internal dashboard that loads a prepared storm scenario, ranks assets by risk with a
plain-words reason beside each rank, and records every recommendation and decision.
**It recommends; people decide.**

## The specification is not in this repository

It lives at `spec/` on the working machine and is deliberately **not committed**. Every task
is driven from it, and nothing under `spec/01-docs/` is ever an output of a task.

| Before any task, read | Path |
|---|---|
| **Rules for an AI agent** | `spec/06-agent/01-instructions/AGENT.md` |
| The workspace entry point | `spec/CLAUDE.md` |
| The next unit of work | `spec/02-tasks/01-planning/task-index.md` |
| The context slice for that task | `spec/06-agent/02-context/context-pack.md` |

If `spec/` is absent, **stop and ask** — do not infer the specification from the code.

## Layout

```
backend/    FastAPI / Python - api, store, scoring, loader   (ADR-008)
frontend/   Next.js / TypeScript - views                     (ADR-008)
spec/       local only, never committed
```

## Never

- **Never commit `.env` or any `*.db` file.** The database holds the append-only decision
  record (ADR-002, ADR-004).
- **Never write `UPDATE` or `DELETE` against `decision_records`**, and never drop its two
  triggers inside an unrelated migration.
- **Never let the model score, rank, or band anything** (ADR-009). It phrases reasons the
  scorer computed, and only factor names and contributions enter a prompt.
- **Never answer an open question by guessing.** Stop and ask.

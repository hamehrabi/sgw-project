# ADR-008: A Python/FastAPI backend, with Next.js as a separate frontend

**ADR ID:** ADR-008
**Status:** Accepted
**Date:** 2026-08-15
**Decision owner:** The developer (sole owner for the prototype — Q-026)
**Review date:** At the first live source-system connection

---

## Context

Q-027 answered the stack as Next.js and TypeScript in one process, with SQLite via
`better-sqlite3` and migrations through `drizzle-kit`. That answer was given on the reasoning
that one language means one toolchain for the agent, and one process matches ADR-001 and ADR-002.

Two things have changed since:

- **The backend is to be Python and FastAPI.** The frontend stays Next.js.
- **ADR-009 introduces a hosted language model** used to phrase computed reasons. The Python
  ecosystem is where that work is least awkward.

Two gaps in the Q-027 stack also pushed this way, and both are named in the record rather than
discovered here: Next.js has no background-job runner, and REQ-NF-003 depends on the parse not
holding a web worker; and `drizzle-kit` does not generate triggers, while ADR-004 puts BR-004's
entire enforcement in two of them.

## Options considered

1. **Stay with Next.js in one process**, add a worker thread for the parse and a hand-written
   SQL migration for the triggers. Keeps ADR-001 literally true and keeps one language. Costs
   the LLM work sitting in the ecosystem where it is most awkward, and leaves the trigger
   migration permanently at risk from a `drizzle-kit generate`.
2. **Next.js frontend, FastAPI backend — two processes, two languages.** Costs the single-process
   property ADR-001 chose, and the one-toolchain property Q-027 chose. Buys a background-job
   story that already exists, raw-SQL migrations that carry triggers naturally, and the
   ecosystem the model work lives in.
3. **Python end to end**, serving templates rather than a Next.js client. One language again, and
   it discards the component specification in `frontend-component-spec.md`, which is written
   against React-shaped components.

*Compared on:* which interface is simpler · which is more general · which forces callers
to do work that should be inside · which is cheaper to reverse.

## Decision

**Next.js (TypeScript) frontend calling a FastAPI (Python) backend.** SQLite remains the store;
the driver becomes Python's `sqlite3` or SQLAlchemy, and migrations become raw SQL through a
Python migration tool.

**The module boundaries from ADR-001 survive the split**, and now run along a process line for
two of them: `views/` is the Next.js application; `api/`, `scoring/`, `loader/` and `store/` are
Python packages inside the FastAPI service.

## Reason

The split is bought for two concrete gaps rather than for preference. The parse must not run in
a request handler — REQ-NF-003's promise that the app keeps answering and names the failing file
depends on it — and FastAPI has `BackgroundTasks` with Celery, RQ or `arq` behind it if the job
outgrows that. And a Python migration tool writes the `decision_records` triggers as ordinary
SQL, which removes the standing risk that a schema-first migration generator quietly drops
BR-004's only enforcement.

ADR-001's *reason* survives even though its *literal claim* does not: it chose a modular monolith
because the scoring module had to be separable from the views that display it, and FF-002 needed
a boundary it could inspect. A process boundary is a stronger version of that, not a weaker one —
a view in a different language cannot import the scorer even by accident.

## Consequences

- **Positive:** Background work has a home. Triggers are written as SQL and cannot be generated
  away. The LLM work in ADR-009 sits in its native ecosystem. FF-002 becomes structurally
  impossible to violate rather than merely checked.
- **Trade-off or limitation:** **Two languages and two toolchains**, which is exactly what Q-027
  chose against — an agent now needs both, and a task that crosses the boundary is two reviews.
  Two processes to deploy, start, and keep in step. The single-process claim in ADR-001 is no
  longer true and this ADR says so rather than leaving that document quietly wrong.
- **Rule the AI assistant must follow during implementation:** The frontend never queries the
  store directly — it calls the API. The scoring module is Python and is never reimplemented,
  mirrored, or partially duplicated in the frontend for display purposes. Migrations are raw SQL
  and always re-assert both `decision_records` triggers.

> **If no trade-off is visible, keep looking.** A choice with no downside was never a
> choice — you are comparing in the abstract instead of weighted for this context.

## Compliance

| Enforced by | Where |
|---|---|
| FF-001, FF-002 — now checked across a process boundary as well as an import graph | [`../../04-technical-spec/fitness-functions.md`](../../04-technical-spec/fitness-functions.md) |

## Revisit when

The two-process overhead costs more than the background-job and migration problems it solved —
observable as deployment friction rather than as a feeling. Or if the frontend and backend start
sharing types by hand, which is the first symptom of a boundary that wants to be one process.

## Impact

| Dimension | Impact |
|---|---|
| Security | Neutral internally. **STEST-010 must be reworded**: the frontend now makes network calls to the backend, so *zero outbound calls* becomes *no call to any system outside the platform*. |
| Reliability | Positive. Background work no longer competes with request handling. |
| Performance | Neutral at this size; one internal network hop per request. |
| Cost | Neutral — still one VM, two processes. |
| Maintainability | Mixed. Cleaner boundaries, two toolchains. The honest cost is that the workspace's "one language" argument is gone. |

## Related

- Related requirements: REQ-NF-003, REQ-NF-005, BR-004
- Amends: ADR-001 (one process → two), ADR-002 (driver and migration tooling only; the store is unchanged)
- Answers: the background-job gap and the trigger-generation gap raised against Q-027
- Supersedes / superseded by: — (partially supersedes Q-027's server half)

---

> Blueprint: blueprints/01-docs/05-architecture/architecture-decisions/ADR-000-template.md

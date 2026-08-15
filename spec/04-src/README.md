# 04-src/ — Application Code

> Source: Ch. 4 §4.3 (`/src` stores the application code) + Ch. 12 §12.4 (file map).

The layout below mirrors the file map the book gives an AI agent so it does not create
duplicate folders, place code in the wrong layer, or ignore the structure you already
chose. Adapt it to your stack, then **update the file map in
[`../agent/context-pack.md`](../06-agent/02-context/context-pack.md)** so the agent sees the real
structure.

```
04-src/
  pages/          # screen-level frontend pages
  components/     # reusable interface pieces
  api/            # API route handlers or client calls
  services/       # business logic
  data/           # data access and schema helpers
```

**This folder is empty.** No code has been written — the workspace holds the specification the
code will be built from, and TASK-001 is the first thing that puts a file here.

**Adapted to ADR-001's five modules.** The generic layout above and this project's module set
are the same shape with different names, and the agent must build the second, not the first:

```
04-src/
  views/          # screens and components (ADR-001: "views")
  api/            # routes, request validation, response shape, auth and role checks
  scoring/        # THE CORE SUBDOMAIN. The only module that produces a score,
                  #   a rank, or a reason. No view may import it (FF-002).
  loader/         # parse, validate, apply the seven defect rules, match assets
  store/          # schema, migrations, queries, and the two append-only triggers
```

The name `services/` is deliberately absent. ADR-001 splits what a generic `services/` folder
would hold into **scoring** and **loader**, because those two have different rules and only one
of them is the core subdomain. A single `services/` folder is how a scoring rule ends up beside
a file parser with nothing saying they are different kinds of thing.

---

## Layer responsibilities (Ch. 8 §8.4, Ch. 20 §20.3)

| Folder | Owns | Must **not** do |
|---|---|---|
| `pages/`, `components/` | Screens, forms, display states, user actions. | Contain database queries or hidden business rules. |
| `api/` | Routes, request validation, response formatting. | Hide complex domain logic in route handlers. |
| `services/` | Business rules and core decisions. | Depend directly on screen layout or format HTTP responses. |
| `data/` | Database access, queries, persistence. | Decide user-facing business behavior. |

### The same table, for this project's modules

| Module | Owns | Must **not** do |
|---|---|---|
| `views/` | Rendering, the five states, what the user is offered. | Compute a score or a rank. **Import `scoring/`** — FF-002 fails the build. |
| `api/` | Identity, role checks, request validation, response shape. | Contain a scoring rule or a matching rule. |
| `scoring/` | The score, the rank, and the reasons — produced by one computation, never separately (ADR-005). | Read a request, know about a screen, or write anywhere but its own results. |
| `loader/` | Parsing, the seven defect rules, matching assets across differing codes. | Score anything. Resolve an unmatched record by guessing. |
| `store/` | Durable state, and the constraints that make BR-002, BR-003 and BR-004 true. | Decide user-facing behaviour. |

> **Architecture rule:** a boundary is useful only when you can tell whether a piece of
> code belongs inside or outside it.

---

## Rules for code in this folder

- Every module traces back to a requirement → [`../docs/traceability.md`](../01-docs/08-traceability/traceability.md)
- Validation runs **before** business logic.
- Secrets come from the environment, never from source.
- Error messages are safe for users; details go to logs.
- Behavior changes ship with tests in [`../tests/`](../03-tests/).

Five more apply here, each traced to a decision rather than to taste:

- **No view imports `scoring/`.** FF-002 fails the build (ADR-001).
- **No `UPDATE` or `DELETE` is ever written against `decision_records`**, and neither trigger is
  dropped or recreated inside an unrelated migration (ADR-004).
- **No training step, model file, or learned parameter** enters version one, and the reasons come
  out of the same computation as the score (ADR-005).
- **No outbound network call exists**, at any version — not to a source system, not to a service
  (BR-005, CON-005, CON-006). STEST-010 asserts the absence.
- **A constraint the store could enforce is never implemented in the service layer instead**
  (ADR-002). A rule that lives only in code is removed by the first refactor with every test
  still green.

---

> Blueprint: blueprints/04-src/README.md

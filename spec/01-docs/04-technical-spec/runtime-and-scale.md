# runtime-and-scale.md — Limits, Cache, Scale, Cost

> **Purpose:** the four runtime layers that are invisible until they hurt.
> **When you use it:** with the technical spec, before implementation.
> **Covers:** rate limiting · cache & CDN · load balancing & scalability · compute & cost.

> **Most projects will answer "not needed" to half of this file — and that is the point.**
> An explicit *"no CDN: single region, 50 users, static assets are 40 KB"* is a decision.
> Silence is an accident waiting for traffic. Fill it in fifteen minutes and move on.

> ### What every "Needed?" cell must contain
>
> **`☐ Not needed` on its own is not an answer.** It is the same blank as an empty cell, spelled
> differently, and it reads as a row somebody skipped rather than a row somebody decided.
>
> Every refusal takes both halves:
>
> - ***why:*** — the fact that makes it unnecessary *today*. "Single user, 40 KB of assets",
>   not "not required".
> - ***revisit when:*** — the change that would make it necessary. A number, an event, a
>   question id. **Without one, a refusal expires silently**: the project grows past the reason
>   and nothing says so, because the reason was never written as a threshold.
>
> **One exception, and it must be stated in the row:** a refusal on *principle* has no revisit
> trigger, because no number could reverse it — *"refused on principle: the health check has to
> answer during an incident, and no traffic level makes throttling it correct."* Write
> ***why:*** and then say which kind of refusal it is. That is a stronger answer than a
> threshold, and it is only honest when the row says so rather than leaving the trigger off.

---

## 1. Rate limiting

Protects three different things. Say which one you are protecting — they need different limits.

| Protecting against | Typical limit | Applies to |
|---|---|---|
| **Abuse / DoS** | per IP | public endpoints |
| **Runaway cost** | per user per day | anything that calls a paid API |
| **Noisy neighbour** | per tenant | shared infrastructure |

| Endpoint / group | Limit | Window | Scope | On exceed | Needed? |
|---|---|---|---|---|---|
| Login | 5 per account, 20 per IP | 10 min / 1 min | per IP + per account | 429 + `Retry-After` | ✅ — the per-account half is the one that matters; an IP limit alone is walked past by a distributed attempt. |
| Scenario upload | 1 concurrent | — | per user | 429 + `Retry-After` | ✅ — the most expensive request in the product and the only one that parses untrusted input. Two at once from one admin is a mistake, not a workload. |
| Write endpoints | — | — | per user | — | ☐ Not needed — *why:* under 50 signed-in users inside one organisation, and every write is already role-checked and written to the decision record. *revisit when:* the platform becomes reachable from outside SGW's own network, **or** users pass 200. |
| **Reason phrasing (LLM)** | `LLM_MAX_CALLS_PER_RANKING`, plus a monthly cost ceiling | per ranking, and per month | per ranking + global | Stop calling the provider; **fall back to computed reason text** | ✅ **cost control.** This row's own revisit trigger fired: it said *"any endpoint calls a metered service — on that day an unlimited endpoint is an unlimited invoice"*, and ADR-009 is that day. A ranking phrases up to 220 reasons; unbounded, one storm is an unbounded bill. |
| Everything else | — | — | — | — | ☐ Not needed — *why:* reads are cheap, internal, and served to a known set of signed-in people. *revisit when:* the first live source-system connection is made, which is what turns predictable internal load into something driven from outside. |

**Rules**
- Return **429** with `Retry-After`. Never fail silently or drop the request.
- Rate limiting is **authorization-adjacent**: it must be enforced server-side, and it
  needs a **deny test** like any other rule.
- Login needs limiting **per account as well as per IP** — otherwise a distributed
  attempt walks straight past an IP limit.
- If a paid API sits behind an endpoint, an unlimited endpoint is an **unlimited invoice**.

## 2. Cache & CDN

> The hard part is never the cache. It is **invalidation** — decide it now, in writing.

| What | Where | TTL | Invalidated by | Stale is acceptable? | Needed? |
|---|---|---|---|---|---|
| Static assets | — | — | — | yes | ☐ Not needed — *why:* one internal instance, under 50 users on SGW's own network; the app serves its own assets. *revisit when:* the platform is reachable from outside that network, **or** the asset payload passes 1 MB. |
| Reference data | — | — | — | yes | ☐ Not needed — *why:* a scenario is written once and read many times, but it already sits in the database on the same host. A second copy is a second thing to invalidate for a saving nobody has measured. *revisit when:* REQ-NF-001's re-rank limit is missed and profiling names this read as the cause. |
| Expensive query | — | — | — | — | ☐ Not needed — *why:* performance was offered as a driver in Round 4 and not chosen, and a cache is a correctness risk before it is a performance win. *revisit when:* the re-rank limit in REQ-NF-001 is missed against a real prepared dataset (Q-017). |
| Per-user data | — | — | — | **usually no** | ☐ Not needed — **refused on principle.** *why:* every user is in one organisation and sees the same ranking, so there is no per-user view to cache. If one ever appears, caching it in a shared store without the user in the key is the classic cross-tenant leak — and it passes every functional test, because every test uses one user. No traffic number makes that correct. |

**Rules**
- Never cache **per-user data in a shared cache** without the user ID in the key. This is
  the classic cross-tenant leak, and it will pass every functional test.
- Every cached item needs a **named invalidation trigger**. "It expires eventually" is not one.
- Prefer **content-hashed filenames** over CDN purges.
- A cache is a **correctness risk before it is a performance win**. If performance is not
  one of your three driving characteristics, you probably do not need one yet.

## 3. Load balancing & scalability

| Question | Answer |
|---|---|
| Is the app **stateless**? | **Yes.** Nothing that matters lives in process memory; a restart loses in-flight requests and nothing else. |
| Where do **sessions** live? | Server-side, in the store, checked on every request (ADR-003, DD-007). **Never sticky** — sticky means not stateless, and it is the one option that shuts the door this row exists to hold open, for nothing in return today. Lifetime: 240 minutes idle, 12 hours absolute (ADR-006). |
| Scaling trigger | Not applicable — single instance. |
| Min / max instances | 1 / 1 |
| **Background workers** | **Yes, for one thing:** parsing an uploaded scenario must not run inside a request handler. A file of unknown size cannot be allowed to hold a web worker, and REQ-NF-003's promise — the app keeps answering and names the file that failed — depends on the app still being able to answer. Whether that is a separate process or a queued job is Round 5's decision. |
| **Database connections** | A small pool on a single instance, far below any provider limit. Nothing to compute at this size. |
| Long-running work | The scenario parse, and only that. Handled as above. |

> **Statelessness is the option that buys horizontal scaling later.** It costs almost
> nothing on day one and is expensive to retrofit. Even if you never scale out, being
> stateless means a restart is not an incident.

☐ **Single instance is fine** — *why:* under 50 users in the first six months, and scalability
was explicitly rejected as a driver in Round 4 with that reason recorded.
*revisit when:* concurrent users pass 200, **or** the first live source-system connection is
made — that is the change that turns a predictable internal load into an externally driven one.

Statelessness is kept anyway, with one instance, because it costs nothing now and means a
restart mid-storm is invisible rather than an incident. That is buying an option cheaply.

## 4. Compute & cost

| Item | Value |
|---|---|
| Compute shape | Undecided — Round 8 asks where this runs. Until then the design assumes only that it is one process with a disk. |
| Instance size | Follows the compute shape. Undecided. |
| **Monthly cost ceiling** | **Zero recurring third-party spend** (CON-006), plus one small VM. Any non-zero third-party line item is itself the alert: it means a dependency was added without a decision (Q-019). |
| Cost per unit | Not a meaningful figure at under 50 internal users on one instance, and inventing one would imply a model nobody built. |
| Biggest cost driver | The instance itself. CON-006 removes every metered service, which is exactly what makes this row dull — and dull is the win. |
| Quotas & hard limits | None known. There is no provider yet (Round 8). |
| Alert at | Any third-party charge at all. With a ceiling of zero, a percentage threshold has nothing to measure — the first invoice is the signal. |

> **Cost is an architectural characteristic.** It behaves like latency: unmeasured, it
> only surfaces as a surprise. A cost ceiling with an alert is the cheapest fitness
> function in this whole template.

---

> Blueprint source: this file is new to the template — added to close the runtime layers
> (rate limiting, cache/CDN, scaling, cost) that the spec-driven method does not cover.

---

> Blueprint: blueprints/01-docs/04-technical-spec/runtime-and-scale.md

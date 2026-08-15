# Frontend Component Specification

> Source: Ch. 7 §7.4 + Ch. 27 §27.6.
> Tells the agent what components to create, what data they receive, what states they must
> handle, and how they behave when filters or permissions change.

---

## Component table

| Component | Purpose | Data needed | States | Rules |
|---|---|---|---|---|
| `AppShell` | Frame: navigation, scenario selector, current user and role. | current user, role, loaded scenarios | loading, ready, unauthorized | Render no content until the signed-in role is known. The scenario selector is always present, because everything below it is scoped to one scenario. |
| `ScenarioUploadPanel` | Drag-and-drop upload of a prepared storm. | upload progress, parse result, unmatched-asset count | idle, uploading, parsing, success, error, permission denied | Refuse over-size or wrong-type files **before** parsing, naming the file and the reason. A failed parse leaves every already-loaded scenario untouched. Hidden for a non-admin **and** refused by the server (REQ-R-001). |
| `ScenarioSwitcher` | Choose among the loaded storms. | loaded scenarios: name, source note, loaded date | loading, success, empty, error | The empty state reads "no storm loaded yet" and points an admin at the upload panel. It must never render as a scenario with no risk. |
| `AssetTable` | The joined asset view. | paginated asset page, each value with source and age | loading, success, empty, error, unauthorized | Every value shows its source and age, and an estimated value is visually distinct from a measured one (BR-003). Assets flagged `needs review` are surfaced, never quietly hidden. |
| `RiskList` | Every asset ordered by risk. | ranked page for one forecast revision | loading, success, empty, error, unauthorized | **A rank never renders without its reasons** (BR-002). The empty state reads "no ranking computed" — never "no risk". |
| `ReasonPanel` | The plain-words reasons behind one rank, and the values they rest on. | reasons, contributing values with source and age | loading, success, error | Opening it is recorded: success metric 3 counts how often a rank is acted on without it being opened. |
| `ForecastRevisionControl` | Apply the scenario's next forecast change and compare orders. | current and available revisions | idle, applying, success, error | The previous order stays reachable after re-ranking (AC-005). Re-ranking never destroys what was shown before. |
| `PlacementForm` | Record a crew placement against the ranking. | ranked assets, current revision | idle, validating, saving, success, error, permission denied | Keeps every typed value on error. A placement lost mid-storm is worse than an error message. |
| `RecommendationDecision` | Accept, change, or reject a recommendation. | the recommendation, existing decision if any | idle, saving, success, error, already decided | Change and reject require a note. A second decision shows the first rather than overwriting it (BR-004). |
| `DispatchBoard` | The shared damage and repair job list. | damage reports and jobs for the scenario | loading, success, empty, error | Two reports at one location render as one job, never two (AC-007). The empty state reads "no damage reported", never "all clear". |
| `DismissAlarmControl` | Clear a false alarm in one action. | the report | idle, saving, error | One action, but never anonymous — it captures who dismissed it and why (REQ-F-008). |
| `StalenessBanner` | State how old the data is, and say so loudly once it is old enough to be wrong. | `forecast_issued_at`, the current time, `SCENARIO_STALE_AFTER_HOURS` | hidden, visible | **Restated by CHG-013.** Every screen states the data's origin time and age **always**; the banner appears once that age passes `SCENARIO_STALE_AFTER_HOURS` (6 — the National Hurricane Center issues full advisories every 6 hours, so older data means a newer forecast almost certainly exists and is not on screen). It is not dismissible — the whole point is that it outlasts the reader's attention. Its old trigger, *the last good picture is being shown instead of current data*, could never fire: reads are served from stored rows, so what is shown **is** the current data (`technical-spec.md` §6). A missing source file is reported by `ScenarioIntegrityNotice` to an admin, not by this banner — the asset view stays correct, so degrading it would be a lie in the safe direction. |

**Example (Ch. 27 §27.6)**

| Component | Purpose | Data needed | States | Rules |
|---|---|---|---|---|
| `DashboardShell` | Page frame: navigation, title, tenant selector. | current user, tenant, route | loading, ready, unauthorized | Do not show content until tenant access is confirmed. |
| `FilterBar` | Date, feature, plan, role filters. | available filters, current filter state | ready, validating | Changing filters refreshes all dependent views. |
| `KpiCardGrid` | Shows summary metrics. | summary metrics | loading, success, empty, error | Cards must explain what each metric means. |
| `TrendChart` | Time-series metrics. | daily metric points | loading, success, empty, error | Empty charts must not appear as zero performance. |
| `ReportTable` | Lists saved reports. | report list | loading, success, empty, error | Only show reports visible to the current role. |
| `ExportPanel` | Queues and tracks exports. | export job status | idle, queued, ready, failed | Export button only appears for permitted roles. |

---

## Per-component template

```
Component name:
Purpose:
Supports requirement: REQ-###

Props / inputs:
  - name: type — required/optional — meaning

Internal state:

States to handle:
  - Loading:            [what the user sees]
  - Success:            [what the user sees]
  - Empty:              [what the user sees — must not look like an error or a zero]
  - Error:              [safe message + recovery action]
  - Disabled:           [when and why]
  - Permission denied:  [what is hidden vs. what is explained]

User actions:

Validation shown inline:

Accessibility notes:
  - Labels:
  - Keyboard navigation:
  - Error announcement:

Out of scope for this component:
```

**One component is specified in full below, and eleven are not.**
[`../01-intent/subdomain-map.md`](../01-intent/subdomain-map.md) gives the ranked risk list Full
spec depth and every other area Light, so `RiskList` — the component the product is judged on —
is written out here and the rest are specified when their task is written in Round 7. That is
the depth allocation being spent, not an unfinished section.

```
Component name:       RiskList
Purpose:              Show every asset in the loaded scenario ordered by risk, with the
                      plain-words reasons for each rank visible beside it.
Supports requirement: REQ-F-002, REQ-F-003, AC-003, AC-004, BR-002

Props / inputs:
  - scenarioId:       string  — required — the loaded storm
  - forecastRevision: integer — optional — defaults to the scenario's current revision
  - pageSize:         integer — optional — 1..500, default 100

Internal state:
  - items, cursor, status: loading | success | empty | error
  - expandedAssetId — which ReasonPanel is open

States to handle:
  - Loading:           Skeleton rows at the eventual row height, so nothing shifts when
                       data arrives. Never a blank frame during a storm.
  - Success:           Ranked rows. Every row carries its reasons inline or an always-
                       visible control that opens them — never a row with no route to why.
  - Empty:             "No ranking has been computed for this storm yet." Plus what to do
                       about it. It must NEVER read as "no assets are at risk" — an empty
                       ranking rendered as safety is the most dangerous screen in the
                       product.
  - Error:             "We could not load the ranking." Plus Retry. If a previous ranking
                       is held, show it with StalenessBanner rather than nothing.
  - Disabled:          Re-rank control disabled while a revision is being applied.
  - Permission denied: Not reachable — every signed-in user may read the ranking. A
                       signed-out request is handled by AppShell, not here.

User actions:         scroll, page, open reasons, sort within rank ties, select an asset

Validation shown inline:
  - An out-of-range forecastRevision shows "that forecast revision does not exist for this
    storm" rather than silently falling back to the current one. A silent fallback would
    show one ranking while the reader believes they are looking at another.

Accessibility notes:
  - Labels:            Rank, score and confidence are labelled text, never colour alone.
                       A red row that means nothing without colour vision is not a ranking.
  - Keyboard:          The list and every ReasonPanel are reachable and operable by
                       keyboard alone.
  - Error announcement: Load failures and staleness are announced, not only shown — a
                       banner nobody's screen reader mentions is a banner during a storm.
  - Standard:          Which formal standard applies is undecided — see Q-013. The three
                       rules above hold regardless of what it answers.

Out of scope for this component:
  - Computing the score (the scoring module owns it, and no view imports it — FF-002)
  - Editing an asset, assigning a crew, or any write of any kind
```

---

## The five states rule

Every data-bound component must handle **all five**. Missing states are where shallow
AI-generated UIs fail (Ch. 27 §27.3).

| State | Requirement |
|---|---|
| Loading | Show progress; never a blank frame. |
| Success | Render the data. |
| **Empty** | Explain *why* it is empty and how data appears. Never render an empty result as a zero value. |
| **Error** | Safe message + retry option. Never a stack trace. |
| **Permission denied** | Hide or disable; do not reveal protected resource details. |

**The empty state carries unusual weight in this product.** Three components can be empty for
innocent reasons and be read as good news: no ranking computed looks like no risk, no damage
reported looks like all clear, and no storm loaded looks like a quiet day. Each one is specified
above with wording that cannot be misread that way, because a reassuring blank screen during a
hurricane is a failure mode the five-states rule exists to catch.

---

## Frontend requirement areas (Ch. 7 §7.4)

| Area | Specify |
|---|---|
| Screens or pages | Dashboard, login, settings, list view, detail view, form page. |
| Components | Navigation, table, card, modal, form, search bar, filter, status badge. |
| Form fields | Required, optional, input type, placeholder, validation rule. |
| UI states | Loading, empty, error, success, disabled, permission-denied. |
| User actions | Create, edit, delete, save, cancel, search, filter, export, retry. |
| Accessibility basics | Readable labels, keyboard-friendly navigation, clear error messages. |

---

> **Security rule (Ch. 27 §27.7):** hiding a button in the frontend is helpful for the
> user interface, but it is **not security by itself**. Enforce permissions on the server.

---

> Blueprint: blueprints/01-docs/04-technical-spec/frontend-component-spec.md

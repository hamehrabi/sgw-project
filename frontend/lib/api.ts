/**
 * The only way the interface reaches data.
 *
 * The frontend never queries the store — it calls the API (ADR-008). Nothing here computes
 * a score, a rank, or a band: that is `scoring/`, it lives in the other process, and a view
 * cannot import it even by accident (FF-002).
 */

export type Role = 'admin' | 'operator'

export interface Identity {
  user_id: string
  name: string
  role: Role
  /** CHG-053: true while the password is an admin-set temporary one. The shell shows the
   *  change screen and nothing else; the server refuses every other route regardless. */
  must_change_password: boolean
}

export interface ApiError {
  code: string
  message: string
}

export class RequestFailed extends Error {
  readonly status: number
  readonly code: string
  /** The whole refusal body — some refusals carry more than a sentence (the summary
   *  approval's 409 carries the verification table that blocked it). */
  readonly body: ApiError & Record<string, unknown>

  constructor(status: number, body: ApiError & Record<string, unknown>) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.body = body
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    // The session cookie is HttpOnly: script cannot read it, and this is what attaches it.
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...init.headers },
  })

  if (response.status === 204) {
    return undefined as T
  }

  const body = await response.json().catch(() => ({
    code: 'unreachable',
    message: 'We could not reach the server. Please try again.',
  }))

  if (!response.ok) {
    throw new RequestFailed(response.status, body as ApiError & Record<string, unknown>)
  }
  return body as T
}

/** One displayable value. Source and age are structural, never optional (BR-003). */
export interface AssetValue {
  name: string
  value: string | number | null
  source: string | null
  observed_at: string | null
  estimated: boolean
}

export interface Asset {
  asset_id: string
  external_ids: string[]
  name: string
  type: string
  location: { lat: number; lon: number }
  match_status: 'matched' | 'needs_review'
  values: AssetValue[]
}

export interface Integrity {
  intact: boolean
  missing_files: string[]
  affects: string[]
}

/** One forecast the prepared storm carries, and the time it was issued for. */
export interface ForecastRevisionEntry {
  forecast_revision: number
  valid_time: string
  /**
   * Whether this revision has a ranking that can be read back (CHG-027).
   *
   * The list is every forecast **the prepared file carries** and it is complete from the moment
   * the storm is loaded; a ranking exists only where somebody has applied one. Offering the two
   * as one list is how the control came to draw a button whose only possible answer was the 404
   * `technical-spec.md` §7.3 requires — a revision that is *coming* is not an order that can be
   * compared.
   */
  ranked: boolean
}

export interface Scenario {
  scenario_id: string
  name: string
  forecast_revision: number
  /**
   * Every revision this storm carries — a property of the prepared file, not a running
   * total. The control offers what exists and nothing else.
   */
  forecast_revisions: ForecastRevisionEntry[]
  /** Null once the storm is at its last forecast: there is nothing further to apply. */
  next_forecast_revision: number | null
  loaded_at: string
  forecast_issued_at: string | null
  /** Stated always, never only when bad — silence must not teach the reader "fresh". */
  data_age_hours: number | null
  stale: boolean
  stale_after_hours: number
  integrity: Integrity
}

/**
 * One storm in the list of loaded storms — `ScenarioSwitcher`'s input (CHG-030).
 *
 * `frontend-component-spec.md` asks for *name, source note, loaded date*. The age travels with
 * them because AC-010 requires every screen to state how old its data is **always**, and a
 * switcher naming a six-day-old storm as though it were current would be the first screen to
 * break that rule.
 *
 * There is no asset here, no coordinate and no neighbourhood, and there is not going to be one:
 * a count is the finest thing this response carries (CON-003, REQ-NF-007).
 */
export interface LoadedScenario {
  scenario_id: string
  name: string
  /** Which prepared dataset this is, and where it came from — as the admin typed it. */
  source_note: string
  loaded_at: string
  forecast_revision: number
  forecast_issued_at: string | null
  data_age_hours: number | null
  stale: boolean
  asset_count: number
  /**
   * Whether this storm's current revision has an order behind it. A storm can be loaded and
   * unranked; a switcher that could not tell would offer the reader an empty screen, which is
   * CHG-027's argument one component over.
   */
  ranked: boolean
}

export interface LoadedScenarios {
  items: LoadedScenario[]
  total: number
}

/** What applying a forecast change produced. A new revision — never a rewritten one. */
export interface ForecastRevisionApplied {
  scenario_id: string
  forecast_revision: number
  /** Still readable, and still the order any decision was made against (AC-005). */
  previous_forecast_revision: number
  valid_time: string
  computed_at: string
  ranked: number
  unscored: number
  next_forecast_revision: number | null
}

export interface AssetPage {
  scenario_id: string
  items: Asset[]
  needs_review_count: number
}

export interface Reason {
  factor: string
  strength: 'Strong' | 'Moderate' | 'Slight'
  contribution: number
  /** Plain words, computed alongside the score. This is what ships if no model phrases it. */
  detail: string
}

export interface RiskItem {
  asset_id: string
  external_ids: string[]
  name: string
  type: string
  rank: number | null
  score: number | null
  band: 'High' | 'Medium' | 'Low' | null
  reasons: Reason[]
  /** Set when the asset could not be scored. It is in the ranking, not ranked. */
  unscored_reason: string | null
  weight_set_version: string
  match_status: 'matched' | 'needs_review'
  values: AssetValue[]
}

export interface DecisionRecorded {
  decision_record_id: string
  recommendation_id: string
  decision: string
  actor_user_id: string
  occurred_at: string
}

export const recommendations = {
  /** Records a decision. **Never dispatches anything** (BR-001). */
  decide: (recommendationId: string, decision: string, note: string | null) =>
    request<DecisionRecorded>(`/api/v1/recommendations/${recommendationId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, note }),
    }),
}

/**
 * A recorded crew placement (REQ-F-005).
 *
 * **A record, never an action** (BR-001). Nothing was dispatched, nobody was assigned, no repair
 * job was created and no message left the platform — this is a row in the append-only decision
 * record saying what a person decided while looking at one particular ranking.
 *
 * There is no location field and there is not going to be one: the "where" is a list of assets,
 * because CON-003 forbids storing anything finer and the store has nowhere to put it.
 */
export interface PlacementRecorded {
  placement_id: string
  scenario_id: string
  /** The revision the operator was **reading**, which is not always the storm's current one. */
  forecast_revision: number
  /** The delivered ranking this was made against, when one has been delivered. */
  recommendation_id: string | null
  crew: string
  asset_ids: string[]
  note: string | null
  actor_user_id: string
  occurred_at: string
}

export const placements = {
  /** Records where a crew waits. **Never dispatches anything** (BR-001). */
  record: (
    scenarioId: string,
    crew: string,
    assetIds: string[],
    forecastRevision: number,
    note: string | null,
  ) =>
    request<PlacementRecorded>(`/api/v1/scenarios/${scenarioId}/placements`, {
      method: 'POST',
      body: JSON.stringify({
        crew,
        asset_ids: assetIds,
        forecast_revision: forecastRevision,
        note,
      }),
    }),
}

export interface Ranking {
  scenario_id: string
  /** The audit row this delivered ranking was recorded as (FF-005). Decisions reference it. */
  recommendation_id: string
  forecast_revision: number
  computed_at: string | null
  weight_set_version: string | null
  /** Always false in version one — the weights have never been validated (ADR-007, CHG-014). */
  weights_calibrated: boolean
  items: RiskItem[]
  total: number
  /**
   * The next page of **this storm's** ranking at **this revision**, or null on the last page.
   *
   * Opaque, and it carries its own scope: a cursor handed to another storm is refused rather
   * than applied, because a page of one storm's ranking served under another storm's name is
   * REQ-F-010's blend with no visible symptom.
   */
  next_cursor: string | null
}

/**
 * A damage report. **Its location is a neighbourhood and can be nothing else** — the store
 * refuses anything finer (CON-003, REQ-NF-007), so no screen and no export has a household
 * to leak. An asset is named by `asset_id`, never by a coordinate.
 */
export interface DamageReport {
  report_id: string
  asset_id: string | null
  repair_job_id: string | null
  location: { neighbourhood: string | null }
  reported_at: string
  reported_by: string
  status: 'open' | 'duplicate' | 'dismissed'
  /** CHG-050: what this call accounts for. Null is "the caller did not say" — not zero. */
  customers_out: number | null
  asset_is_critical: boolean
}

export interface RepairJob {
  job_id: string
  status: 'pending' | 'in_progress' | 'done'
  /** Null in version one. The board is never ordered by a score, rank or band. */
  priority_rank: number | null
  /** A note about what people decided. The platform assigns nobody (BR-001). */
  assigned_to: string | null
  /**
   * The neighbourhood of the **first report ever filed** for this job, not of the first still
   * open — dismissing a false alarm hides a report from the working list, it does not unsay
   * where the job is (CHG-020).
   */
  location: { neighbourhood: string | null }
  created_at: string
  updated_at: string
  /** Reports still on the working list. */
  report_count: number
  /** Reports dismissed as false alarms, so a job with nothing open reads as explained. */
  dismissed_report_count: number
  /**
   * CHG-050: derived from IMPACT — a critical facility among the open reports' assets,
   * then customers accounted for — and never from a risk score. The frozen vocabulary:
   * High / Medium / Low, never "Critical", never "Standard".
   */
  priority: 'High' | 'Medium' | 'Low'
  customers_out: number
  reports: DamageReport[]
}

export interface Board {
  scenario_id: string
  items: RepairJob[]
  /**
   * Reports that belong to no repair job. `repair_job_id` is optional in the schema and a
   * report belongs "to at most one repair job", so the state exists — and a board that groups
   * only by job leaves those reports on no screen at all (CHG-022). A report nobody can find is
   * the radio call AC-007's second half exists to keep.
   */
  unattached_reports: DamageReport[]
  job_count: number
  /** Every report still on the working list, attached to a job or not. */
  report_count: number
  dismissed_report_count: number
}

/**
 * A cleared false alarm (REQ-F-008).
 *
 * `dismissal_id` is the row in the append-only record. It is here because *never anonymous* is
 * a claim about a record, and a caller that cannot name the record cannot check the claim.
 */
export interface Dismissal {
  report_id: string
  scenario_id: string
  repair_job_id: string | null
  location: { neighbourhood: string | null }
  status: 'dismissed'
  dismissed_by: string
  dismissed_reason: string
  dismissal_id: string
  occurred_at: string
}

/** The bound and the blank alphabet a dismissal reason is judged by, re-exported from the one
 *  module that holds them so this file has no second copy of either (CHG-037). The rule is the
 *  server's; these exist only so the field cannot grow past what a `400` would refuse and the
 *  button is not offered for a reason that is not one. */
export { DISMISSAL_REASON_MAX, trimDismissalReason } from './dismissal'

export const dispatch = {
  board: (id: string) => request<Board>(`/api/v1/scenarios/${id}/jobs`),

  /** Two reports at one location join one job — decided by the server, never by this list. */
  fileReport: (
    id: string,
    neighbourhood: string,
    assetId: string | null,
    customersOut: number | null = null,
  ) =>
    request<DamageReport>(`/api/v1/scenarios/${id}/damage-reports`, {
      method: 'POST',
      body: JSON.stringify({
        neighbourhood,
        asset_id: assetId,
        customers_out: customersOut,
      }),
    }),

  /**
   * Clear a false alarm. **One action, and never anonymous** (REQ-F-008): the reason travels
   * with the request and who dismissed it comes from the session, so there is no shape of this
   * call that records neither. Nothing is dispatched, cancelled or closed — the repair job the
   * report was filed against stays on the board (BR-001, CHG-020).
   */
  dismiss: (reportId: string, reason: string) =>
    request<Dismissal>(`/api/v1/damage-reports/${reportId}/dismiss`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
}

export const scenarios = {
  /**
   * Every storm that is loaded, newest first (REQ-F-010, US-002).
   *
   * Readable by both roles: loading a storm is privileged, choosing which loaded storm to look
   * at is the product (`technical-spec.md` §7.2).
   */
  list: () => request<LoadedScenarios>('/api/v1/scenarios'),

  /**
   * Omitting `forecastRevision` asks for the storm's current one. Passing an earlier value
   * returns that earlier ranking **unchanged** (AC-005); passing one the storm does not carry
   * is a 404 and never a quiet substitution of the current list.
   */
  risks: (id: string, forecastRevision?: number) =>
    request<Ranking>(
      forecastRevision === undefined
        ? `/api/v1/scenarios/${id}/risks`
        : `/api/v1/scenarios/${id}/risks?forecast_revision=${forecastRevision}`,
    ),

  /**
   * Apply the storm's next forecast change and re-rank (REQ-F-004). A write that produces a
   * new revision; nothing that was ranked before is altered, and no crew is moved (BR-001).
   */
  applyNextForecast: (id: string) =>
    request<ForecastRevisionApplied>(`/api/v1/scenarios/${id}/forecast-revisions`, {
      method: 'POST',
    }),

  read: (id: string) => request<Scenario>(`/api/v1/scenarios/${id}`),
  assets: (id: string) => request<AssetPage>(`/api/v1/scenarios/${id}/assets`),

  load: async (name: string, sourceNote: string, files: FileList | File[]) => {
    const form = new FormData()
    form.append('name', name)
    form.append('source_note', sourceNote)
    for (const file of Array.from(files)) form.append('files', file)

    const response = await fetch('/api/v1/scenarios', {
      method: 'POST',
      credentials: 'same-origin',
      body: form, // no Content-Type: the browser sets the multipart boundary
    })
    const body = await response.json().catch(() => ({
      code: 'unreachable',
      message: 'We could not reach the server. Please try again.',
    }))
    if (!response.ok) throw new RequestFailed(response.status, body as ApiError & Record<string, unknown>)
    return body as { scenario_id: string; forecast_revision: number }
  },

  /**
   * The same POST, through XMLHttpRequest so the upload's real progress is reportable —
   * `fetch` cannot see bytes leave the machine. `onProgress` receives 0..100 while the
   * bytes travel; the parse that follows has no percentage, and the panel says so in
   * words rather than inventing one (`reliability-specification.md` §6: one
   * undifferentiated spinner hides which stage broke).
   */
  loadWithProgress: (
    name: string,
    sourceNote: string,
    files: File[],
    onProgress: (percent: number) => void,
  ) =>
    new Promise<{ scenario_id: string; forecast_revision: number }>((resolve, reject) => {
      const form = new FormData()
      form.append('name', name)
      form.append('source_note', sourceNote)
      for (const file of files) form.append('files', file)

      const xhr = new XMLHttpRequest()
      xhr.open('POST', '/api/v1/scenarios')
      xhr.responseType = 'json'
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
      }
      xhr.onload = () => {
        const body = (xhr.response ?? {
          code: 'unreachable',
          message: 'We could not reach the server. Please try again.',
        }) as ApiError & Record<string, unknown>
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as unknown as { scenario_id: string; forecast_revision: number })
        } else {
          reject(new RequestFailed(xhr.status, body))
        }
      }
      xhr.onerror = () =>
        reject(
          new RequestFailed(0, {
            code: 'unreachable',
            message: 'We could not reach the server. Nothing was changed.',
          }),
        )
      xhr.send(form)
    }),
}

export const auth = {
  signIn: (email: string, password: string) =>
    request<Identity>('/api/v1/auth/session', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  /** Who am I, and in which role. The only way `AppShell` learns the role after a reload. */
  current: () => request<Identity>('/api/v1/auth/session'),

  signOut: () => request<void>('/api/v1/auth/session', { method: 'DELETE' }),

  /** CHG-053: replace the caller's own password. The current one is verified first. */
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>('/api/v1/auth/password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
}

// --- The interface rebuild's reads and records (CHG-040..CHG-054) -------------------------

export interface Finding {
  finding_id: string
  defect: number
  code: string
  subject: string
  message: string
  affected_file: string
  needs_decision: boolean
  resolution: string | null
  resolved_by: string | null
  resolved_at: string | null
}

export interface FindingsPage {
  scenario_id: string
  items: Finding[]
  needs_decision_count: number
  total: number
}

/** One side of a withheld merge, in the fields the comparison card shows. */
export interface MatchRecord {
  id: string
  name: string
  type: string
  condition: string | null
  condition_observed_at: string | null
  install_year: number | null
}

export interface MatchCandidate {
  candidate_id: string
  asset_id: string
  map_record: MatchRecord
  candidate_record: MatchRecord
  /** A word, never a percentage: the rule is a position threshold and a name comparison. */
  confidence: 'high' | 'moderate'
  resolution: 'pending' | 'match' | 'not_match'
  resolved_by: string | null
  resolved_at: string | null
}

export interface MatchQueue {
  scenario_id: string
  items: MatchCandidate[]
  pending_count: number
  total: number
}

export interface Depot {
  service_area_id: string
  name: string
  customer_count: number
  crews: number
}

export interface StagingPlan {
  scenario_id: string
  depots: Depot[]
  /** Context, not a recommendation: no per-depot figure can be defended (CHG-049). */
  high_risk_count: number
  recorded_at: string | null
  recorded_by: string | null
  forecast_revision: number | null
}

export interface SummaryVerificationEntry {
  kind: 'figure' | 'noun' | 'vocabulary'
  token: string
  allowed: boolean
  platform_value: unknown
}

export interface Summary {
  summary_id: string
  scenario_id: string
  state: 'Draft' | 'Approved' | 'Sent'
  draft_text: string
  approved_text: string | null
  /** "Drafted from platform data" survived the verifier; "Assembled" is the fallback. */
  label: 'Drafted from platform data' | 'Assembled from platform data'
  source_figures: Record<string, unknown>
  verification: { ok: boolean; entries: SummaryVerificationEntry[] }
  drafted_at: string
  drafted_by: string
  approved_by: string | null
  approved_at: string | null
}

export interface ActivityEntry {
  kind: 'human' | 'system'
  text: string
  occurred_at: string
}

export interface MovementItem {
  asset_id: string
  previous_rank: number | null
  current_rank: number | null
  band: 'High' | 'Medium' | 'Low' | null
  reason_factor: string
  reason_detail: string
  previous_label: string
}

export interface Movement {
  scenario_id: string
  forecast_revision: number
  /** True at revision 0: there is no earlier order, and the strip says so plainly. */
  first_ranking: boolean
  previous_label: string | null
  items: MovementItem[]
  moved_up_high: number
}

export const insights = {
  findings: (id: string) => request<FindingsPage>(`/api/v1/scenarios/${id}/findings`),

  resolveFinding: (id: string, findingId: string, resolution: string) =>
    request<Finding>(`/api/v1/scenarios/${id}/findings/resolve`, {
      method: 'POST',
      body: JSON.stringify({ finding_id: findingId, resolution }),
    }),

  matches: (id: string) => request<MatchQueue>(`/api/v1/scenarios/${id}/matches`),

  resolveMatch: (id: string, candidateId: string, resolution: 'match' | 'not_match') =>
    request<MatchCandidate>(`/api/v1/scenarios/${id}/matches/resolve`, {
      method: 'POST',
      body: JSON.stringify({ candidate_id: candidateId, resolution }),
    }),

  staging: (id: string) => request<StagingPlan>(`/api/v1/scenarios/${id}/staging`),

  /** Records counts a person chose. Nothing is dispatched — there is no path (BR-001). */
  recordStaging: (id: string, forecastRevision: number, depots: { service_area_id: string; crews: number }[]) =>
    request<StagingPlan>(`/api/v1/scenarios/${id}/staging`, {
      method: 'POST',
      body: JSON.stringify({ forecast_revision: forecastRevision, depots }),
    }),

  summary: (id: string) =>
    request<{ scenario_id: string; summary: Summary | null }>(
      `/api/v1/scenarios/${id}/summary`,
    ),

  draftSummary: (id: string) =>
    request<Summary>(`/api/v1/scenarios/${id}/summary/draft`, { method: 'POST' }),

  approveSummary: (id: string, summaryId: string, approvedText: string) =>
    request<Summary>(`/api/v1/scenarios/${id}/summary/approve`, {
      method: 'POST',
      body: JSON.stringify({ summary_id: summaryId, approved_text: approvedText }),
    }),

  markSummarySent: (id: string, summaryId: string) =>
    request<Summary>(`/api/v1/scenarios/${id}/summary/send`, {
      method: 'POST',
      body: JSON.stringify({ summary_id: summaryId }),
    }),

  activity: (id: string) =>
    request<{ scenario_id: string; items: ActivityEntry[] }>(
      `/api/v1/scenarios/${id}/activity`,
    ),

  movement: (id: string) => request<Movement>(`/api/v1/scenarios/${id}/movement`),

  /** The bundled dataset, through the same parse path as a real upload. Admin only. */
  loadSample: () =>
    request<{ scenario_id: string; forecast_revision: number }>('/api/v1/scenarios/sample', {
      method: 'POST',
    }),

  /**
   * One person's decision about one asset's rank (CHG-055). Recorded, appended, never
   * an action: a Dismiss records disagreement with a rank — it does not hide the asset.
   */
  triage: (
    id: string,
    assetId: string,
    forecastRevision: number,
    action: 'Accept' | 'Adjust' | 'Dismiss',
    note: string | null,
  ) =>
    request<{
      decision_record_id: string
      action: string
      asset_code: string
      forecast_revision: number
      occurred_at: string
    }>(`/api/v1/scenarios/${id}/triage`, {
      method: 'POST',
      body: JSON.stringify({
        asset_id: assetId,
        forecast_revision: forecastRevision,
        action,
        note,
      }),
    }),
}

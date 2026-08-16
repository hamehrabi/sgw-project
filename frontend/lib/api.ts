/**
 * The only way the interface reaches data.
 *
 * The frontend never queries the store — it calls the API (ADR-008). Nothing here computes
 * a score, a rank, or a band: that is `scoring/`, it lives in the other process, and a view
 * cannot import it even by accident (FF-002).
 */

export type Role = 'admin' | 'user'

export interface Identity {
  user_id: string
  name: string
  role: Role
}

export interface ApiError {
  code: string
  message: string
}

export class RequestFailed extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, body: ApiError) {
    super(body.message)
    this.status = status
    this.code = body.code
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
    throw new RequestFailed(response.status, body as ApiError)
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

export interface Scenario {
  scenario_id: string
  name: string
  forecast_revision: number
  loaded_at: string
  forecast_issued_at: string | null
  /** Stated always, never only when bad — silence must not teach the reader "fresh". */
  data_age_hours: number | null
  stale: boolean
  stale_after_hours: number
  integrity: Integrity
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

export const dispatch = {
  board: (id: string) => request<Board>(`/api/v1/scenarios/${id}/jobs`),

  /** Two reports at one location join one job — decided by the server, never by this list. */
  fileReport: (id: string, neighbourhood: string, assetId: string | null) =>
    request<DamageReport>(`/api/v1/scenarios/${id}/damage-reports`, {
      method: 'POST',
      body: JSON.stringify({ neighbourhood, asset_id: assetId }),
    }),
}

export const scenarios = {
  risks: (id: string) => request<Ranking>(`/api/v1/scenarios/${id}/risks`),

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
    if (!response.ok) throw new RequestFailed(response.status, body as ApiError)
    return body as { scenario_id: string; forecast_revision: number }
  },
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
}

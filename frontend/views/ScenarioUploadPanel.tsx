'use client'

/**
 * ScenarioUploadPanel — drag-and-drop a prepared storm.
 *
 * Six states, and the progression matters: *idle → uploading → parsing → success* or
 * *error*, plus *permission denied*. "One undifferentiated spinner would hide which stage
 * broke, which is the difference between a fixable file and a broken system"
 * (`reliability-specification.md` §6).
 *
 * Hidden for a non-admin **and** refused by the server (SEC-Z-002). Hiding it here is for
 * the user; the 403 is the security. STEST-005 calls the endpoint directly for that reason.
 *
 * A refusal names the file and changes nothing: every already-loaded storm keeps working,
 * which is the promise FTEST-001 asserts on the other side of the boundary.
 */

import { useState } from 'react'

import { RequestFailed, scenarios } from '@/lib/api'
import { isBlank, trimBlank } from '@/lib/blank'

type State =
  | { stage: 'idle' }
  | { stage: 'uploading' }
  | { stage: 'parsing' }
  | { stage: 'success'; scenarioId: string }
  | { stage: 'error'; message: string }

const EXPECTED = 'manifest.json plus assets.csv, maintenance.csv, weather.csv and outages.csv'

/**
 * What goes in `source_note` when the admin leaves the field blank.
 *
 * `data-and-integration-spec.md` §3 makes the note part of the request body and the server
 * requires it, so the panel has always sent this string — a stub, because until TASK-009
 * nothing stored the note or showed it. It is kept as the fallback rather than made mandatory:
 * making the field required would refuse a load during a storm over a sentence, and the note is
 * how a reader tells two prepared datasets apart, not how the system does (that is the content
 * digest, CHG-031).
 */
const UNSTATED_SOURCE = 'uploaded via the panel'

export function ScenarioUploadPanel({
  role,
  onLoaded,
}: {
  role: 'admin' | 'user'
  onLoaded: (scenarioId: string) => void
}) {
  const [state, setState] = useState<State>({ stage: 'idle' })
  const [name, setName] = useState('')
  const [sourceNote, setSourceNote] = useState('')

  if (role !== 'admin') return null

  async function send(files: FileList | File[]) {
    // `isBlank`, never `String.prototype.trim()`. A storm named U+00A0 was stored and the
    // switcher drew a row with no visible label (CHG-039).
    if (isBlank(name)) {
      setState({ stage: 'error', message: 'Name this storm before loading it.' })
      return
    }
    setState({ stage: 'uploading' })
    try {
      // The request returns once parsing has finished; the intermediate stage is shown
      // because the parse is the slow half and the one that can fail.
      setState({ stage: 'parsing' })
      const created = await scenarios.load(
        trimBlank(name),
        trimBlank(sourceNote) || UNSTATED_SOURCE,
        files,
      )
      setState({ stage: 'success', scenarioId: created.scenario_id })
      onLoaded(created.scenario_id)
    } catch (error) {
      setState({
        stage: 'error',
        message:
          error instanceof RequestFailed
            ? error.message
            : 'We could not reach the server. Nothing was changed.',
      })
    }
  }

  return (
    <section
      className="upload"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault()
        void send(event.dataTransfer.files)
      }}
      data-testid="upload-panel"
    >
      <h2>Load a prepared storm</h2>

      <label htmlFor="storm-name">Storm name</label>
      <input
        id="storm-name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Helene replay"
      />

      {/* `database-design.md` §3: *which prepared dataset this is, and where it came from.* It
          is the field `ScenarioSwitcher` shows beside each storm's name, and it is how a person
          tells two loaded storms apart when both are called something plausible. */}
      <label htmlFor="storm-source-note">Where this came from</label>
      <input
        id="storm-source-note"
        value={sourceNote}
        onChange={(event) => setSourceNote(event.target.value)}
        placeholder="NOAA 2024 replay pack"
      />

      <label htmlFor="storm-files">Files — {EXPECTED}</label>
      <input
        id="storm-files"
        type="file"
        multiple
        onChange={(event) => event.target.files && void send(event.target.files)}
      />

      <p className="upload__hint">Or drag the folder&rsquo;s files onto this panel.</p>

      {state.stage === 'uploading' && <p role="status">Uploading…</p>}
      {state.stage === 'parsing' && <p role="status">Parsing and joining the records…</p>}
      {state.stage === 'success' && (
        <p role="status" data-testid="upload-success">
          Loaded. This storm is now selectable alongside any others.
        </p>
      )}
      {state.stage === 'error' && (
        <p role="alert" data-testid="upload-error">
          {state.message}
        </p>
      )}
    </section>
  )
}

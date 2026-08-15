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

type State =
  | { stage: 'idle' }
  | { stage: 'uploading' }
  | { stage: 'parsing' }
  | { stage: 'success'; scenarioId: string }
  | { stage: 'error'; message: string }

const EXPECTED = 'manifest.json plus assets.csv, maintenance.csv, weather.csv and outages.csv'

export function ScenarioUploadPanel({
  role,
  onLoaded,
}: {
  role: 'admin' | 'user'
  onLoaded: (scenarioId: string) => void
}) {
  const [state, setState] = useState<State>({ stage: 'idle' })
  const [name, setName] = useState('')

  if (role !== 'admin') return null

  async function send(files: FileList | File[]) {
    if (!name.trim()) {
      setState({ stage: 'error', message: 'Name this storm before loading it.' })
      return
    }
    setState({ stage: 'uploading' })
    try {
      // The request returns once parsing has finished; the intermediate stage is shown
      // because the parse is the slow half and the one that can fail.
      setState({ stage: 'parsing' })
      const created = await scenarios.load(name, 'uploaded via the panel', files)
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

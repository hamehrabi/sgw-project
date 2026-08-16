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
 *
 * "Use sample storm data" goes through the same parse path as a real upload — the button
 * asks the server to read the bundled dataset, and everything after that is identical.
 * It is not a shortcut, and the quality summary it produces is measured, never canned.
 */

import { FileUp } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input, Label } from '@/components/ui/field'
import { insights, RequestFailed, scenarios } from '@/lib/api'
import { isBlank, trimBlank } from '@/lib/blank'

type State =
  | { stage: 'idle' }
  | { stage: 'uploading' }
  | { stage: 'parsing' }
  | { stage: 'success'; scenarioId: string }
  | { stage: 'error'; message: string }

const EXPECTED = 'manifest.json plus assets.csv, maintenance.csv, weather.csv and outages.csv'

/**
 * What goes in `source_note` when the admin leaves the field blank. Kept as a fallback
 * rather than made mandatory: requiring the field would refuse a load during a storm
 * over a sentence (CHG-031's surroundings).
 */
const UNSTATED_SOURCE = 'uploaded via the panel'

export function ScenarioUploadPanel({
  role,
  onLoaded,
}: {
  role: 'admin' | 'operator'
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

  async function sample() {
    setState({ stage: 'parsing' })
    try {
      const created = await insights.loadSample()
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
    <Card data-testid="upload-panel">
      <CardHeader>
        <CardTitle>Load a prepared storm</CardTitle>
        <CardDescription>
          Review and load a prepared scenario. Nothing is sent to any live system.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="storm-name">Storm name</Label>
            <Input
              id="storm-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Helene replay"
            />
          </div>
          <div>
            {/* §3: *which prepared dataset this is, and where it came from* — the field
                the switcher shows beside each storm's name. */}
            <Label htmlFor="storm-source-note">Where this came from</Label>
            <Input
              id="storm-source-note"
              value={sourceNote}
              onChange={(event) => setSourceNote(event.target.value)}
              placeholder="NOAA 2024 replay pack"
            />
          </div>
        </div>

        <div
          className="rounded-card border-2 border-dashed border-line-strong bg-rail px-6 py-10 text-center"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault()
            void send(event.dataTransfer.files)
          }}
        >
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-teal-soft">
            <FileUp className="h-5 w-5 text-teal-deep" aria-hidden />
          </div>
          <p className="text-[15px] font-medium">
            Drop your asset, maintenance, weather and outage files here
          </p>
          <p className="mt-1 text-[13px] text-muted">
            {EXPECTED}. Nothing is sent to any live system.
          </p>
          <div className="mt-4">
            <Label htmlFor="storm-files" className="sr-only">
              Files — {EXPECTED}
            </Label>
            <input
              id="storm-files"
              type="file"
              multiple
              className="mx-auto block max-w-xs text-[13px] text-muted file:mr-3 file:rounded-card file:border file:border-line file:bg-background file:px-3 file:py-1.5 file:text-[13px] file:font-medium file:text-ink hover:file:bg-panel"
              onChange={(event) => event.target.files && void send(event.target.files)}
            />
          </div>
        </div>

        {state.stage === 'uploading' && (
          <p role="status" className="text-[13px] text-muted">
            Uploading…
          </p>
        )}
        {state.stage === 'parsing' && (
          <p role="status" className="text-[13px] text-muted">
            Parsing and joining the records…
          </p>
        )}
        {state.stage === 'success' && (
          <p
            role="status"
            data-testid="upload-success"
            className="text-[13px] font-medium text-low-fg"
          >
            Loaded. This storm is now selectable alongside any others.
          </p>
        )}
        {state.stage === 'error' && (
          <p role="alert" data-testid="upload-error" className="text-[13px] text-high-fg">
            {state.message}
          </p>
        )}
      </CardContent>
      <CardFooter className="justify-between">
        <Button variant="link" onClick={() => void sample()}>
          Use sample storm data
        </Button>
        <p className="text-[12px] text-muted">
          Loading goes through the same checks as any upload — size, content, and all
          seven data-defect rules.
        </p>
      </CardFooter>
    </Card>
  )
}

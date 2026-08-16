'use client'

/**
 * ScenarioUploadPanel — stage the files, see what is missing, then process.
 *
 * **The staging list exists because of three real refusals in the log**: uploads went to
 * the server with `manifest.json` absent, and the person learned it from a 422 after the
 * fact. Now the panel knows the five names a prepared scenario is made of, shows which
 * are staged and which are missing, badges anything that is not part of the format in
 * the server's own words, and only offers **Process data** when the set is complete —
 * the error became guidance before the POST instead of a refusal after it.
 *
 * The stages stay distinct — *staging → uploading (a real percentage) → processing →
 * done* or *error* — because "one undifferentiated spinner would hide which stage broke,
 * which is the difference between a fixable file and a broken system"
 * (`reliability-specification.md` §6). The upload has a true percentage (XHR sees the
 * bytes); the parse does not, and the bar says "processing" in words rather than
 * inventing one.
 *
 * Hidden for a non-admin **and** refused by the server (SEC-Z-002). Hiding it here is
 * for the user; the 403 is the security — STEST-005 calls the endpoint directly.
 *
 * The client-side completeness check is a courtesy, not the rule: the server refuses an
 * incomplete or mistyped upload independently, and a refusal names the file and changes
 * nothing (FTEST-001).
 */

import { CheckCircle2, CircleDashed, FileUp, X } from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/bits'
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
  | { stage: 'staging' }
  | { stage: 'uploading'; percent: number }
  | { stage: 'processing' }
  | { stage: 'done'; scenarioId: string }
  | { stage: 'error'; message: string }

/** The five names a prepared scenario is made of — the same list the server requires. */
const EXPECTED = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

/**
 * What goes in `source_note` now that the panel no longer asks for it: a human sentence
 * naming the door the data came through. CHG-031's point survives — the column holds
 * words a reader can use, never a digest.
 */
const UNSTATED_SOURCE = 'uploaded via the panel'

export function ScenarioUploadPanel({
  role,
  onLoaded,
}: {
  role: 'admin' | 'operator'
  onLoaded: (scenarioId: string) => void
}) {
  const [state, setState] = useState<State>({ stage: 'staging' })
  const [name, setName] = useState('')
  const [staged, setStaged] = useState<File[]>([])

  if (role !== 'admin') return null

  const stagedNames = new Set(staged.map((file) => file.name))
  const missing = EXPECTED.filter((expected) => !stagedNames.has(expected))
  const unrecognised = staged.filter((file) => !EXPECTED.includes(file.name))
  const busy = state.stage === 'uploading' || state.stage === 'processing'
  const complete = missing.length === 0 && unrecognised.length === 0

  function stage(added: FileList | File[]) {
    // Materialised NOW, not inside the state updater: a FileList is a LIVE collection
    // tied to its input, and this handler clears that input — an updater that read it
    // later found it already empty, and the staged list silently stayed blank.
    const incoming = Array.from(added)
    // Later picks replace earlier files of the same name — re-dropping a corrected
    // manifest must not leave the broken one in the set.
    setStaged((current) => {
      const kept = current.filter(
        (file) => !incoming.some((candidate) => candidate.name === file.name),
      )
      return [...kept, ...incoming]
    })
    if (state.stage === 'error' || state.stage === 'done') setState({ stage: 'staging' })
  }

  function unstage(fileName: string) {
    setStaged((current) => current.filter((file) => file.name !== fileName))
  }

  async function process() {
    if (isBlank(name)) {
      setState({ stage: 'error', message: 'Name this data source before processing it.' })
      return
    }
    setState({ stage: 'uploading', percent: 0 })
    try {
      const created = await scenarios.loadWithProgress(
        trimBlank(name),
        UNSTATED_SOURCE,
        staged,
        (percent) => {
          setState({ stage: 'uploading', percent })
          // The bytes have all left; what remains is the parse, which has no percentage.
          if (percent >= 100) setState({ stage: 'processing' })
        },
      )
      setState({ stage: 'done', scenarioId: created.scenario_id })
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
    setState({ stage: 'processing' })
    try {
      const created = await insights.loadSample()
      setState({ stage: 'done', scenarioId: created.scenario_id })
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
          Stage the five prepared files, then process them. Nothing is sent to any live
          system.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="max-w-sm">
          <Label htmlFor="storm-name">Source name</Label>
          <Input
            id="storm-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Helene replay"
            disabled={busy}
          />
        </div>

        <div
          className="rounded-card border-2 border-dashed border-line-strong bg-rail px-6 py-8 text-center"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault()
            stage(event.dataTransfer.files)
          }}
        >
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-teal-soft">
            <FileUp className="h-5 w-5 text-teal-deep" aria-hidden />
          </div>
          <p className="text-[15px] font-medium">
            Drop your asset, maintenance, weather and outage files here
          </p>
          <p className="mt-1 text-[13px] text-muted">
            manifest.json plus assets.csv, maintenance.csv, weather.csv and outages.csv.
          </p>
          <div className="mt-4">
            <Label htmlFor="storm-files" className="sr-only">
              Files
            </Label>
            <input
              id="storm-files"
              type="file"
              multiple
              disabled={busy}
              className="mx-auto block max-w-xs text-[13px] text-muted file:mr-3 file:rounded-card file:border file:border-line file:bg-background file:px-3 file:py-1.5 file:text-[13px] file:font-medium file:text-ink hover:file:bg-panel"
              onChange={(event) => {
                if (event.target.files) stage(event.target.files)
                event.target.value = ''
              }}
            />
          </div>
        </div>

        {/* ---- The staging list: what is here, what is missing, what does not belong ---- */}
        {(staged.length > 0 || state.stage !== 'staging') && (
          <ul className="divide-y divide-line rounded-card border border-line" data-testid="staged-files">
            {EXPECTED.map((expected) => {
              const file = staged.find((candidate) => candidate.name === expected)
              return (
                <li key={expected} className="flex items-center justify-between gap-3 px-3 py-2">
                  <span className="flex items-center gap-2 text-[13px]">
                    {file ? (
                      <CheckCircle2 className="h-4 w-4 text-low-fg" aria-hidden />
                    ) : (
                      <CircleDashed className="h-4 w-4 text-faint" aria-hidden />
                    )}
                    {expected}
                    {file && (
                      <span className="text-[11px] text-faint">
                        {(file.size / 1024).toFixed(1)} KB
                      </span>
                    )}
                  </span>
                  {file ? (
                    <span className="flex items-center gap-2">
                      <Badge variant="low">Staged</Badge>
                      {!busy && (
                        <button
                          type="button"
                          aria-label={`Remove ${expected}`}
                          className="text-faint hover:text-ink"
                          onClick={() => unstage(expected)}
                        >
                          <X className="h-3.5 w-3.5" aria-hidden />
                        </button>
                      )}
                    </span>
                  ) : (
                    <Badge variant="outline">Missing</Badge>
                  )}
                </li>
              )
            })}
            {unrecognised.map((file) => (
              <li key={file.name} className="flex items-center justify-between gap-3 px-3 py-2">
                <span className="text-[13px]">{file.name}</span>
                <span className="flex items-center gap-2">
                  {/* The server's own refusal words, shown before the server has to. */}
                  <Badge variant="high">Not part of a prepared scenario</Badge>
                  {!busy && (
                    <button
                      type="button"
                      className="text-[12px] font-medium text-teal underline-offset-2 hover:underline"
                      onClick={() => unstage(file.name)}
                    >
                      Skip file
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}

        {/* ---- The stages, each visibly its own ---- */}
        {state.stage === 'uploading' && (
          <div data-testid="upload-progress">
            <p className="mb-1.5 text-[13px] text-muted" role="status">
              Uploading… {state.percent}%
            </p>
            <Progress value={state.percent} max={100} label="Upload progress" />
          </div>
        )}
        {state.stage === 'processing' && (
          <div data-testid="upload-progress">
            <p className="mb-1.5 text-[13px] text-muted" role="status">
              Upload finished. Processing — parsing, joining and checking the records…
            </p>
            <Progress value={100} max={100} label="Upload finished, processing" className="animate-pulse" />
          </div>
        )}
        {state.stage === 'done' && (
          <p
            role="status"
            data-testid="upload-success"
            className="rounded-card border border-low-fg/25 bg-low-bg px-4 py-2.5 text-[13px] font-medium text-low-fg"
          >
            Data processing finished. Review the data quality summary below, then finish
            and continue to the dashboards.
          </p>
        )}
        {state.stage === 'error' && (
          <p role="alert" data-testid="upload-error" className="text-[13px] text-high-fg">
            {state.message}
          </p>
        )}
      </CardContent>
      <CardFooter className="justify-between">
        <Button variant="link" onClick={() => void sample()} disabled={busy}>
          Use sample storm data
        </Button>
        <div className="flex items-center gap-3">
          {!complete && staged.length > 0 && (
            <p className="text-[12px] text-high-fg">
              {unrecognised.length > 0
                ? 'Remove the files that are not part of a prepared scenario.'
                : `${missing.length} required file(s) still missing.`}
            </p>
          )}
          {/* The screen's one primary action, offered only when it can succeed. */}
          <Button
            variant="primary"
            data-testid="process-data"
            disabled={!complete || busy || state.stage === 'done'}
            onClick={() => void process()}
          >
            {busy ? 'Working…' : 'Process data'}
          </Button>
        </div>
      </CardFooter>
    </Card>
  )
}

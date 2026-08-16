import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * TASK-008 done criterion 11 — REQ-F-008, US-010, `DismissAlarmControl`.
 *
 *     Given  a damage report on the shared board that turns out to be a false alarm
 *     When   the dispatcher clears it
 *     Then   one action does it, it carries who cleared it and why, and nothing is dispatched
 *
 * **The backend tests prove the rows; this proves the screen.** `frontend-component-spec.md`
 * gives `DismissAlarmControl` one rule — *one action, but never anonymous* — and it is a claim
 * about what a dispatcher can and cannot do with their hands. `review-log.md` has recorded three
 * times that a criterion about a screen was satisfied by reading source, and once that deleting
 * the whole control left `tsc`, `lint`, `build` and every browser case green.
 *
 * **The first test must stay first**, for the reason `ATEST-007.spec.ts` gives: one backend, one
 * database and one storm serve the whole run, an identical re-upload resolves to the same
 * scenario, and no endpoint deletes a report — so damage accumulates across files.
 * `fullyParallel: false` keeps declaration order. Every test below names its **own**
 * neighbourhood and asserts only against that job, so work left by another file cannot make one
 * of them pass.
 */

const FIXTURE = path.resolve(
  __dirname,
  '../../spec/03-tests/05-executable/fixtures/storm-with-seven-defects',
)
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

async function loadedStorm(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email').fill('ops@sgw.example')
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByLabel('Storm name').fill('Helene replay')
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURE, name)),
  )
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('dispatch-board')).toBeVisible()
}

async function fileReport(page: Page, neighbourhood: string) {
  const field = page.getByLabel('Report damage in a neighbourhood')
  await field.fill(neighbourhood)
  await page.getByRole('button', { name: 'Add report' }).click()
  await expect(field).toHaveValue('')
}

function jobAt(page: Page, neighbourhood: string) {
  return page.getByTestId('job').filter({ has: page.getByText(neighbourhood, { exact: true }) })
}

test('one press clears a false alarm, and the job it was filed at stays on the board', async ({
  page,
}) => {
  await loadedStorm(page)
  await fileReport(page, 'Kilnwick')
  const job = jobAt(page, 'Kilnwick')
  await expect(job.getByTestId('job-report')).toHaveCount(1)

  await job.getByTestId('dismiss-reason').fill('Tree was already cleared')
  await job.getByTestId('dismiss-submit').click()

  // One action: no confirmation dialog, no second screen. The report leaves the working list.
  await expect(job.getByTestId('job-report')).toHaveCount(0)
  // And the job is still there, still named, reading *explained* rather than *empty* — nothing
  // was dispatched and nothing was cancelled (BR-001, CHG-020).
  await expect(job).toHaveCount(1)
  await expect(job.getByTestId('job-dismissed')).toContainText('1 dismissed as a false alarm')
  await expect(job.getByTestId('job-location')).toHaveText('Kilnwick')
  await expect(page.getByTestId('board-empty')).toHaveCount(0)
})

test('the control is offered on every open report and refuses an empty reason', async ({
  page,
}) => {
  await loadedStorm(page)
  await fileReport(page, 'Marram Dunes')
  const job = jobAt(page, 'Marram Dunes')

  // Never anonymous: with nothing typed there is no way to press it at all.
  await expect(job.getByTestId('dismiss-control')).toBeVisible()
  await expect(job.getByTestId('dismiss-submit')).toBeDisabled()
  await job.getByTestId('dismiss-reason').fill('   ')
  await expect(job.getByTestId('dismiss-submit')).toBeDisabled()

  await job.getByTestId('dismiss-reason').fill('x')
  // Brevity is not the rule — one character is a reason, and the control must not invent a
  // minimum length the server does not have.
  await expect(job.getByTestId('dismiss-submit')).toBeEnabled()
  await job.getByTestId('dismiss-submit').click()
  await expect(job.getByTestId('job-report')).toHaveCount(0)
})

test('a refused dismissal keeps the typed reason and leaves the report on the board', async ({
  page,
}) => {
  await loadedStorm(page)
  await fileReport(page, 'Ferry Gate')
  const job = jobAt(page, 'Ferry Gate')
  // Over the server's bound by one character. The client field is capped at the same number, so
  // the value is set directly — the point of the case is what the screen does with a `400`, and
  // a reason lost to a refused write is the failure this control is written against.
  const tooLong = 'N'.repeat(2001)
  await job.getByTestId('dismiss-reason').evaluate((field, value) => {
    const input = field as HTMLInputElement
    input.removeAttribute('maxlength')
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value',
    )!.set!
    setter.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }, tooLong)

  await job.getByTestId('dismiss-submit').click()

  await expect(job.getByTestId('dismiss-error')).toBeVisible()
  await expect(job.getByTestId('dismiss-error')).toContainText('never an anonymous one')
  await expect(job.getByTestId('dismiss-reason')).toHaveValue(tooLong)
  // Nothing was saved: the alarm is still on the board for somebody to deal with.
  await expect(job.getByTestId('job-report')).toHaveCount(1)
  await expect(job.getByTestId('job-dismissed')).toHaveCount(0)
})

test('clearing one call does not clear the other call about the same place', async ({ page }) => {
  await loadedStorm(page)
  await fileReport(page, 'Cransley')
  await fileReport(page, 'Cransley')
  const job = jobAt(page, 'Cransley')
  await expect(job.getByTestId('job-report')).toHaveCount(2)

  await job.getByTestId('dismiss-reason').first().fill('First call was the wrong street')
  await job.getByTestId('dismiss-submit').first().click()

  // The silent case for the whole feature. One job answers several radio calls, and clearing
  // one of them is not a judgement about the others — a control that cleared the job would pass
  // the first test in this file and lose the second call, which is the failure AC-007's second
  // half exists to prevent.
  await expect(job.getByTestId('job-report')).toHaveCount(1)
  await expect(job.getByTestId('job-count')).toContainText('1 report(s)')
  await expect(job.getByTestId('job-dismissed')).toContainText('1 dismissed')
})

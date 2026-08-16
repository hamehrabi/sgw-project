import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * The interface rebuild's four load-bearing flows (CHG-040, CHG-048, CHG-055), proven
 * with hands on the screen. The backend tests prove the rows; these prove a person can
 * produce them.
 *
 *  1. Focus Mode's keyboard triage writes a decision record the activity rail renders.
 *  2. The summary review's approve block: text the figures cannot back is refused with
 *     the violation named, and the honest text goes through to Sent.
 *  3. The match queue shows both sides of a withheld merge and M resolves it.
 *  4. "Use sample storm data" loads through the same parse path as an upload.
 *  5. The planning screen opens with the answer, pages the ranking, maps the assets
 *     (CHG-057, CHG-058).
 *  6. An asset summary is phrased once, stored, and shown in popup and drawer (CHG-059).
 *  7. A visitor signs up and lands in the app as an operator, never an admin (CHG-061).
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
  await page.getByLabel('Source name').fill('Interface rebuild storm')
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURE, name)),
  )
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
}

test('focus mode triages on the keyboard, and the feed says a person decided', async ({
  page,
}) => {
  await loadedStorm(page)
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()

  await page.getByTestId('start-triage').click()
  await expect(page.getByTestId('focus-mode')).toBeVisible()
  await expect(page.getByTestId('focus-mode')).toContainText('0 of')

  // A — accept, advance. The record is the point; the screen only has to move on.
  await page.keyboard.press('a')
  await expect(page.getByTestId('focus-mode')).toContainText('1 of')

  // D without a note demands the why — a dismissal is worth keeping only with one.
  await page.keyboard.press('d')
  await expect(page.getByLabel('Why dismiss? (required)')).toBeVisible()
  await page.getByLabel('Why dismiss? (required)').fill('asset is offline for planned works')
  await page.getByRole('button', { name: /^Dismiss/ }).click()
  await expect(page.getByTestId('focus-mode')).toContainText('2 of')

  await page.keyboard.press('Escape')
  await expect(page.getByTestId('focus-mode')).toHaveCount(0)

  // The rail: a human deciding, named — never "the system flagged" (CHG-054).
  await page.getByRole('button', { name: 'Dispatch Board' }).click()
  const rail = page.getByTestId('activity-rail')
  await expect(rail).toContainText('accepted the ranking for')
  await expect(rail).toContainText('dismissed the ranking for')
  await expect(rail).not.toContainText('auto-flagged')
  await expect(rail).not.toContainText('sync')
})

test('the summary blocks approval of a figure the platform does not hold', async ({ page }) => {
  await loadedStorm(page)
  await page.getByRole('button', { name: 'Dispatch Board' }).click()

  await page.getByRole('button', { name: /Draft summary|Regenerate/ }).click()
  const card = page.getByTestId('situation-summary')
  await expect(card.getByTestId('summary-state')).toHaveText('Draft')
  // The model is off in this harness: the label must say the figures wrote it.
  await expect(card).toContainText('Assembled from platform data')

  await page.getByRole('button', { name: 'Review and approve' }).click()
  const sheet = page.getByTestId('summary-review')
  await expect(sheet).toBeVisible()
  await expect(page.getByTestId('verification-table')).toBeVisible()

  // A figure nobody supplied. The server refuses it and the refusal is on screen.
  await page.getByLabel('Summary content').fill('An estimated 41,500 customers are without service.')
  await page.getByTestId('approve-summary').click()
  await expect(sheet).toContainText('Approval is blocked until they match.')
  await expect(card.getByTestId('summary-state')).toHaveText('Draft')

  // The honest text goes through — Draft → Approved → Sent in one review.
  await page
    .getByLabel('Summary content')
    .fill('There are 0 open incidents on the board. 0 involve critical facilities.')
  await page.getByTestId('approve-summary').click()
  await expect(card.getByTestId('summary-state')).toHaveText('Sent')
})

test('the match queue shows both sides and M records the reviewer', async ({ page }) => {
  await loadedStorm(page)
  // Processing ends on the Load surface, quality summary already on screen.
  const quality = page.getByTestId('data-quality-summary')
  await expect(quality).toBeVisible()
  // The fixture withholds merges on purpose (defect 1) — the finding offers Review.
  await quality.getByRole('button', { name: 'Review' }).click()

  const sheet = page.getByTestId('match-queue')
  await expect(sheet).toBeVisible()
  await expect(page.getByTestId('match-candidate')).toBeVisible()
  await expect(sheet).toContainText('confidence')
  await expect(sheet).not.toContainText('%')

  const before = await page.locator('text=/\\d+ of \\d+ reviewed/').innerText()
  await page.getByTestId('match-confirm').click()
  await expect(page.locator('text=/\\d+ of \\d+ reviewed/')).not.toHaveText(before)
})

test('the sample button loads a storm through the same parse path', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Email').fill('ops@sgw.example')
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByRole('button', { name: 'Load storm data' }).click()

  await page.getByRole('button', { name: 'Use sample storm data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  // Through the quality summary and the door — a real ranking behind it, not a shortcut.
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()
})

test('the planning screen opens with the answer, pages the ranking, and maps the assets', async ({
  page,
}) => {
  await loadedStorm(page)
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()

  // The answer first (CHG-057): real counts in the headline, the top cards beneath it,
  // each carrying its strongest computed reason and a Review door into the drawer.
  await expect(page.getByTestId('planning-headline')).toContainText(
    'at high risk at the current forecast',
  )
  await expect(page.getByTestId('top-risk-strip')).toBeVisible()
  await expect(page.getByTestId('top-risk-card').first()).toBeVisible()
  await page.getByTestId('top-risk-card').first().getByRole('button', { name: 'Review' }).click()
  await expect(page.getByTestId('asset-sheet')).toBeVisible()

  // CHG-060's stacking fix, held by pointer interception rather than a class name:
  // whatever element is topmost at the drawer's centre must BE the drawer — Leaflet's
  // panes carry z-indexes in the hundreds and used to paint over it.
  const topmostIsDrawer = await page.evaluate(() => {
    const sheet = document.querySelector('[data-testid="asset-sheet"]')
    if (!sheet) return 'no-sheet'
    const box = sheet.getBoundingClientRect()
    const hit = document.elementFromPoint(box.left + box.width / 2, box.top + 40)
    return sheet.contains(hit) ? 'drawer' : (hit?.className.toString() ?? 'nothing')
  })
  expect(topmostIsDrawer).toBe('drawer')
  await page.keyboard.press('Escape')

  // Pagination (CHG-057, CHG-060): 25 by default, expandable, page context stated,
  // previous honest about there being nothing before page one.
  await expect(page.getByTestId('risk-pagination')).toContainText('ranked')
  await expect(page.getByTestId('per-page-25')).toHaveAttribute('aria-pressed', 'true')
  await page.getByTestId('per-page-100').click()
  await expect(page.getByTestId('per-page-100')).toHaveAttribute('aria-pressed', 'true')
  await page.getByTestId('per-page-25').click()
  await expect(page.getByTestId('page-previous')).toBeDisabled()

  // The map (CHG-058): a real Leaflet pane and the mapped count — no key anywhere.
  await expect(page.getByTestId('risk-map')).toBeVisible()
  await expect(page.locator('[data-testid="risk-map"] .leaflet-container')).toBeVisible()
  await expect(page.getByTestId('map-count')).toContainText('mapped')
})

test('an asset summary is phrased once, shown in a popup, and shown in the drawer', async ({
  page,
}) => {
  await loadedStorm(page)
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()

  // The popup (CHG-059). The model is off in this harness, so the label must say the
  // computed factors wrote it — and the verification already happened server-side.
  await page.getByTestId('asset-summary-button').first().click()
  const dialog = page.getByTestId('summary-dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('Assembled from computed factors')
  await page.getByTestId('summary-dialog-close').click()
  await expect(dialog).toHaveCount(0)

  // The same asset's drawer shows the stored summary — one map feeds both, and nothing
  // re-infers on read.
  await page
    .locator('[data-testid="risk-list"] tbody tr')
    .first()
    .locator('td:nth-child(2) button')
    .first()
    .click()
  await expect(page.getByTestId('sheet-summary')).toBeVisible()
  await expect(page.getByTestId('sheet-summary')).toContainText('Assembled from computed factors')
})

test('a visitor signs up and lands in the app as an operator', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('switch-to-sign-up').click()
  await page.getByLabel('Name').fill('Walk-up Operator')
  await page.getByLabel('Email').fill(`walkup.${Date.now()}@sgw.example`)
  await page.getByLabel('Password').fill('walk-up-operator-pass')
  await page.getByRole('button', { name: 'Create account' }).click()

  // Signed in immediately, and as an operator — the server decided the role, and there
  // was no field through which the form could have asked for another.
  await expect(page.getByTestId('role')).toHaveText('operator')
})

test('the worklist assigns, restores and reopens — recorded, never dispatched', async ({
  page,
}) => {
  await loadedStorm(page)
  await page.getByRole('button', { name: 'Dispatch Board' }).click()
  await expect(page.getByTestId('dispatch-board')).toBeVisible()

  // A job exists only because a person filed a report (AC-007's first half).
  await page.getByLabel('Report damage in a neighbourhood').fill('Causeway Flats')
  await page.getByRole('button', { name: 'Add report' }).click()
  const job = page.getByTestId('job').filter({
    has: page.getByText('Causeway Flats', { exact: true }),
  })
  await expect(job).toHaveCount(1)
  await expect(page.getByText('next up')).toBeVisible()

  // Assign: a dialog, a crew label, a record — and the notice says nothing was sent.
  await job.getByTestId('assign-crew').click()
  await page.getByLabel('Crew', { exact: true }).fill('Line crew 2')
  await page.getByTestId('assign-submit').click()
  await expect(page.getByTestId('queue-notice')).toContainText('Assigned Line crew 2')
  await expect(page.getByTestId('queue-notice')).toContainText('no message left the platform')

  // The job moved to the Assigned tab, carrying its crew.
  await page.getByTestId('queue-tab-assigned').click()
  await expect(job).toHaveCount(1)
  await expect(job).toContainText('Line crew 2')

  // Restored, then reopened — a state machine, each step recorded.
  await job.getByTestId('mark-restored').click()
  await page.getByTestId('queue-tab-closed').click()
  await expect(job.getByTestId('reopen-job')).toBeVisible()
  await job.getByTestId('reopen-job').click()
  await page.getByTestId('queue-tab-assigned').click()
  await expect(job).toHaveCount(1)

  // The rail phrases all of it as human acts — never "generated", never "auto".
  const rail = page.getByTestId('activity-rail')
  await expect(rail).toContainText('assigned Line crew 2 to the job at Causeway Flats')
  await expect(rail).toContainText('restored')
  await expect(rail).toContainText('reopened')
  await expect(rail).not.toContainText('generated')
  await expect(rail).not.toContainText('auto-')
})

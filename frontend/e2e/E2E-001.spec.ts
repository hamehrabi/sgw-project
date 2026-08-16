import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * E2E-001 — REQ-F-002…006. TASK-007 done criterion 11, as CHG-060 reshaped it.
 *
 *     Flow name:   Decide against the ranking
 *     Goal:        an operations manager can go from a loaded storm to a recorded
 *                  decision without assembling anything by hand
 *
 * **This is the browser half; the API half is
 * `spec/03-tests/05-executable/integration/test_E2E-001_place_crews_against_ranking.py`.**
 * CHG-060 removed the whole-ranking decision form and the placement form from the
 * planning screen at the client's instruction, so the screen path this file proves is the
 * one that remains: **per-asset triage in the drawer**, each action writing a decision
 * record that names the forecast revision it was taken against. The placement endpoint
 * and its API-level proof stand — a fact about rows stays provable where rows are.
 *
 * **The tests are ordered and the order is load-bearing**, the same way `ATEST-005.spec.ts`
 * and `ATEST-007.spec.ts` document. One backend, one database and one storm serve the whole
 * run; an identical re-upload resolves to the same scenario (§5, replace in place), so the
 * pointer this file advances in the second test stays advanced for the third.
 * `fullyParallel: false` keeps tests inside a file in declaration order.
 *
 * **No other spec loads `storm-for-the-planning-flow`**, which is why it can be advanced
 * here at all — `ATEST-005.spec.ts` says the same thing about its own fixture, and the two
 * would otherwise move each other's pointer underneath them.
 */

const FIXTURE = path.resolve(
  __dirname,
  '../../spec/03-tests/05-executable/fixtures/storm-for-the-planning-flow',
)
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

/** The forecast moves GC-04 from 61 to 155 mph and GC-01 from 96 to 40; these two swap. */
const RISES = 'SS-5566'
const FALLS = 'SS-1042'
/** In the ranking and not ranked — no weather row covers it. Shown, never sorted as safe. */
const UNSCORED = 'LN-8899'

async function loadedStorm(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email').fill('ops@sgw.example')
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByLabel('Source name').fill('Planning flow rehearsal')
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURE, name)),
  )
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('risk-list')).toBeVisible()
}

/** The codes, top to bottom, as a person reads them off the screen. */
async function orderOnScreen(page: Page): Promise<string[]> {
  return page.locator('[data-testid="risk-list"] .row__codes').allInnerTexts()
}

function positionOf(order: string[], code: string): number {
  const index = order.findIndex((row) => row.includes(code))
  expect(index, `${code} is not on the ranking`).toBeGreaterThan(-1)
  return index
}

/** Open the drawer for the top-ranked asset by clicking its name in the table. */
async function openTopAsset(page: Page) {
  await page
    .locator('[data-testid="risk-list"] tbody tr')
    .first()
    .locator('td:nth-child(2) button')
    .first()
    .click()
  await expect(page.getByTestId('asset-sheet')).toBeVisible()
}

test('the planning view reaches a recorded decision, and says nothing was dispatched', async ({
  page,
}) => {
  await loadedStorm(page)

  // Step 2 — read the ranked list, and open the reasons on the top-ranked asset. Every row
  // has a route to why (BR-002); this is the one the manager actually opens.
  const firstRow = page.locator('[data-testid="risk-list"] tbody tr').first()
  await firstRow.getByRole('button', { name: 'Why?' }).click()
  await expect(page.getByTestId('reason-panel').first()).toBeVisible()

  // An asset that could not be scored is on the list, under its own heading, not missing
  // and not sorted as though it were safe.
  await expect(page.getByTestId('unscored-group')).toContainText(UNSCORED)

  // Step 6 — decide about the top-ranked asset, from the drawer (CHG-055, CHG-060).
  await openTopAsset(page)
  await page.getByRole('button', { name: 'Accept ranking' }).click()

  const recorded = page.getByTestId('triage-recorded')
  await expect(recorded).toBeVisible()
  // The record names the revision it was taken against — the sentence the old placement
  // form used to carry, now on the decision itself.
  await expect(recorded).toContainText('forecast revision 0')
  // BR-001, in as many words, because a recorded decision is the thing an operator is
  // most likely to read as an instruction that went somewhere.
  await expect(recorded).toContainText('no crew has been moved')
})

test('after the forecast change, a decision records the revision the operator was reading', async ({
  page,
}) => {
  await loadedStorm(page)
  const before = await orderOnScreen(page)
  expect(positionOf(before, FALLS)).toBeLessThan(positionOf(before, RISES))

  // Steps 3 and 4 — apply the change, and the list re-ranks.
  await page.getByTestId('apply-forecast').click()
  await expect(page.getByTestId('forecast-revisions')).toContainText('Forecast revision 1')
  const after = await orderOnScreen(page)
  expect(positionOf(after, RISES)).toBeLessThan(positionOf(after, FALLS))

  // Step 5 — accept the new order, and the record says revision 1.
  await openTopAsset(page)
  await page.getByRole('button', { name: 'Accept ranking' }).click()
  await expect(page.getByTestId('triage-recorded')).toContainText('forecast revision 1')
  await page.keyboard.press('Escape')

  // And the previous order, still one click away — with a decision recorded against **it**
  // rather than against the list the storm has since moved to. The drawer follows what is
  // being read, not what the pointer says.
  // CHG-057: the comparison chips wait behind a disclosure now — open it first.
  await page.getByTestId('forecast-history-toggle').click()
  await page.getByTestId('view-revision-0').click()
  await expect(page.getByTestId('viewing-earlier')).toContainText('It has not changed')
  expect(await orderOnScreen(page)).toEqual(before)

  await openTopAsset(page)
  await page.getByRole('button', { name: 'Accept ranking' }).click()
  await expect(page.getByTestId('triage-recorded')).toContainText('forecast revision 0')
})

test('a failed save shows the failure and keeps the typed note on screen', async ({
  page,
}) => {
  await loadedStorm(page)

  // The write is failed at the wire rather than in the store, and the split is the point:
  // this half of E2E-001 is *the typed note is still on screen*, which is a fact about the
  // component's error branch. *No row exists* is asserted against the table in the pytest
  // half, where the store itself is made to fail (FTEST-005).
  await page.route('**/api/v1/scenarios/*/triage', (route) =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ code: 'internal_error', message: 'Something went wrong.' }),
    }),
  )

  await openTopAsset(page)
  // Adjust requires the why: the first press asks for it, the second submits it.
  await page.getByRole('button', { name: 'Adjust' }).click()
  await page.getByLabel('Why adjust? (required)').fill('gust figure is stale on this feeder')
  await page.getByRole('button', { name: 'Adjust' }).click()

  // A clear message — and no success anywhere near it.
  await expect(page.getByRole('alert')).toContainText('Something went wrong')
  await expect(page.getByTestId('triage-recorded')).toHaveCount(0)

  // THE TYPED NOTE IS STILL ON SCREEN. A justification lost mid-storm is worse than an
  // error message, and the retype is always longer than the retry.
  await expect(page.getByLabel('Why adjust? (required)')).toHaveValue(
    'gust figure is stale on this feeder',
  )

  // And the retry succeeds against the real endpoint, with the note still typed.
  await page.unroute('**/api/v1/scenarios/*/triage')
  await page.getByRole('button', { name: 'Adjust' }).click()
  await expect(page.getByTestId('triage-recorded')).toBeVisible()
})

test('no ranking on screen, no decision offered against it', async ({ page }) => {
  await loadedStorm(page)

  // BR-001's screen shape: a decision is a decision about a list, and a person takes it
  // while looking at one. A triage door standing beside a ranking that failed to load
  // would invite a decision against nothing.
  await page.route('**/api/v1/scenarios/*/risks*', (route) =>
    route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ code: 'not_found', message: 'This storm has no forecast revision.' }),
    }),
  )
  // CHG-057: the comparison chips wait behind a disclosure now — open it first.
  await page.getByTestId('forecast-history-toggle').click()
  await page.getByTestId('view-revision-0').click()

  await expect(page.getByText('We could not load the ranking')).toBeVisible()
  await expect(page.getByTestId('start-triage')).toHaveCount(0)
  await expect(page.getByTestId('top-risk-strip')).toHaveCount(0)
  // The way back is still on screen — the control is rendered from the scenario, not from
  // the ranking, so a failed read is one failed panel rather than a screen with no exit.
  await expect(page.getByTestId('forecast-revisions')).toBeVisible()
})

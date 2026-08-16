import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * E2E-001 — REQ-F-002…006. TASK-007 done criterion 11.
 *
 *     Flow name:   Place crews against the ranking
 *     Goal:        an operations manager can go from a loaded storm to a recorded crew
 *                  placement without assembling anything by hand
 *
 * **This is the browser half; the API half is
 * `spec/03-tests/05-executable/integration/test_E2E-001_place_crews_against_ranking.py`.** The
 * flow's written expectations divide cleanly and neither half can make the other's claim:
 * *no placement row exists* after a failed save is a fact about a table and needs the **store**
 * made to fail, and *THE TYPED PLACEMENT IS STILL ON SCREEN* is a fact about a screen and needs
 * a browser. `review-log.md` records three separate occasions on which a criterion about a
 * screen was satisfied by reading a `.tsx` file, and `AGENT.md` carries the rule that came out
 * of the third — so `PlacementForm` gets its browser case in the task that writes it rather
 * than in the review that asks for it.
 *
 * **The tests are ordered and the order is load-bearing**, the same way `ATEST-005.spec.ts` and
 * `ATEST-007.spec.ts` document. One backend, one database and one storm serve the whole run;
 * an identical re-upload resolves to the same scenario (§5, replace in place), so the pointer
 * this file advances in the second test stays advanced for the third. `fullyParallel: false`
 * keeps tests inside a file in declaration order.
 *
 * **No other spec loads `storm-for-the-planning-flow`**, which is why it can be advanced here at
 * all — `ATEST-005.spec.ts` says the same thing about its own fixture, and the two would
 * otherwise move each other's pointer underneath them.
 */

const FIXTURE = path.resolve(
  __dirname,
  '../../spec/03-tests/05-executable/fixtures/storm-for-the-planning-flow',
)
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

/** The forecast moves GC-04 from 61 to 155 mph and GC-01 from 96 to 40; these two swap. */
const RISES = 'SS-5566'
const FALLS = 'SS-1042'
/** In the ranking and not ranked — no weather row covers it. A crew may still be placed at it. */
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
  await expect(page.getByTestId('placement-form')).toBeVisible()
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

test('the planning view reaches a recorded placement, and says nothing was dispatched', async ({
  page,
}) => {
  await loadedStorm(page)

  // Step 2 — read the ranked list, and open the reasons on the top-ranked asset. Every row has
  // a route to why (BR-002); this is the one the manager actually opens.
  const firstRow = page.locator('[data-testid="risk-list"] tbody tr').first()
  await firstRow.getByRole('button', { name: 'Why?' }).click()
  await expect(page.getByTestId('reason-panel').first()).toBeVisible()

  // An asset that could not be scored is on the list, under its own heading, not missing and
  // not sorted as though it were safe.
  await expect(page.getByTestId('unscored-group')).toContainText(UNSCORED)

  // Step 6 — record a placement against the current ranking, in two actions: tick the assets,
  // press the button (REQ-NF-004).
  await page.getByLabel('Crew').fill('North crew')
  await page.getByTestId(`placement-asset-${FALLS}`).check()
  await page.getByTestId(`placement-asset-${UNSCORED}`).check()
  await page.getByTestId('placement-note').fill('staged at the depot')
  await page.getByTestId('placement-submit').click()

  const recorded = page.getByTestId('placement-recorded')
  await expect(recorded).toBeVisible()
  // "The placement is saved and shows which revision it was made against."
  await expect(recorded).toContainText('forecast revision 0')
  await expect(recorded).toContainText('North crew')
  await expect(recorded).toContainText(FALLS)
  // BR-001, in as many words, because a control called "placement" is the one an operator is
  // most likely to read as an instruction that went somewhere.
  await expect(recorded).toContainText('No crew has been moved')
})

test('after the forecast change, a placement records the revision the operator was reading', async ({
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

  // Step 5 — accept this ranking.
  await page.getByRole('radio', { name: 'accept' }).check()
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByTestId('decision-recorded')).toBeVisible()

  // Step 6 against revision 1.
  await page.getByLabel('Crew').fill('North crew')
  await page.getByTestId(`placement-asset-${RISES}`).check()
  await page.getByTestId('placement-submit').click()
  await expect(page.getByTestId('placement-recorded')).toContainText('forecast revision 1')

  // And the previous order, still one button away — with a placement recorded against **it**
  // rather than against the list the storm has since moved to. This is done criterion 2 at the
  // screen: the form follows what is being read, not what the pointer says.
  await page.getByTestId('view-revision-0').click()
  await expect(page.getByTestId('viewing-earlier')).toContainText('It has not changed')
  expect(await orderOnScreen(page)).toEqual(before)

  await page.getByRole('radio', { name: 'reject' }).check()
  await page.locator('#decision-note').fill('the earlier order missed the coastal plant')
  await page.getByRole('button', { name: 'Record decision' }).click()
  await expect(page.getByTestId('decision-recorded')).toBeVisible()

  await page.getByLabel('Crew').fill('South crew')
  await page.getByTestId(`placement-asset-${FALLS}`).check()
  await page.getByTestId('placement-submit').click()
  await expect(page.getByTestId('placement-recorded')).toContainText('forecast revision 0')
})

test('a failed save shows the failure and keeps the typed placement on screen', async ({
  page,
}) => {
  await loadedStorm(page)

  // The write is failed at the wire rather than in the store, and the split is the point: this
  // half of E2E-001 is *the typed placement is still on screen*, which is a fact about the
  // component's error branch. *No placement row exists* is asserted against the table in the
  // pytest half, where the store itself is made to fail.
  await page.route('**/api/v1/scenarios/*/placements', (route) =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ code: 'internal_error', message: 'Something went wrong.' }),
    }),
  )

  await page.getByLabel('Crew').fill('Night crew')
  await page.getByTestId(`placement-asset-${RISES}`).check()
  await page.getByTestId('placement-note').fill('two teams staged, radio on channel 4')
  await page.getByTestId('placement-submit').click()

  // A clear message and a retry option — and no success anywhere near it.
  await expect(page.getByTestId('placement-error')).toBeVisible()
  await expect(page.getByTestId('placement-recorded')).toHaveCount(0)

  // THE TYPED PLACEMENT IS STILL ON SCREEN. A placement lost mid-storm is worse than an error
  // message, and the retype is always shorter than the first attempt.
  await expect(page.getByLabel('Crew')).toHaveValue('Night crew')
  await expect(page.getByTestId('placement-note')).toHaveValue(
    'two teams staged, radio on channel 4',
  )
  await expect(page.getByTestId(`placement-asset-${RISES}`)).toBeChecked()

  // And the retry succeeds against the real endpoint, with everything still typed.
  await page.unroute('**/api/v1/scenarios/*/placements')
  await page.getByTestId('placement-submit').click()
  await expect(page.getByTestId('placement-recorded')).toContainText('Night crew')
})

test('no ranking on screen, no placement offered against it', async ({ page }) => {
  await loadedStorm(page)

  // BR-001 as `ScenarioView` already applies it to accept / change / reject: a decision is a
  // decision about a list, and a person takes it while looking at one. A placement form standing
  // beside a ranking that failed to load would invite a placement against nothing.
  await page.route('**/api/v1/scenarios/*/risks*', (route) =>
    route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ code: 'not_found', message: 'This storm has no forecast revision.' }),
    }),
  )
  await page.getByTestId('view-revision-0').click()

  await expect(page.getByText('We could not load the ranking')).toBeVisible()
  await expect(page.getByTestId('placement-form')).toHaveCount(0)
  await expect(page.getByTestId('decision-form')).toHaveCount(0)
  // The way back is still on screen — the control is rendered from the scenario, not from the
  // ranking, so a failed read is one failed panel rather than a screen with no exit.
  await expect(page.getByTestId('forecast-revisions')).toBeVisible()
})

import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * ATEST-005 — REQ-F-004, AC-005. TASK-006 done criterion 12.
 *
 *     Given  a ranked list and a forecast change inside the scenario
 *     When   the change is applied
 *     Then   the list re-ranks, and the previous order remains retrievable for comparison
 *
 * **The API-level test of the same id proves the rows; this proves the screen.** Done criterion
 * 12 is a claim about what an operator can do — *"`ForecastRevisionControl` applies the change
 * and lets the previous order be read back"* — and until this file existed it was satisfied by
 * reading `ForecastRevisionControl.tsx` and by nothing executable. The review that blocked
 * TASK-006 deleted the entire `<ul className="revisions__list">` block — AC-005's comparison
 * half, and the whole of criterion 12 — and `tsc`, `lint`, `build` and all fourteen browser
 * cases stayed green.
 *
 * **The second thing it proves is the one a person found by pressing a button.** `GET
 * /scenarios/{id}` lists the forecasts the prepared **file** carries, so a freshly loaded storm
 * reports revisions `[0, 1, 2]` while only revision 0 has ever been ranked. The control drew one
 * selectable button per entry; clicking *Revision 2* asked for a ranking that did not exist, the
 * server answered the 404 `technical-spec.md` §7.3 requires, and the whole screen went into an
 * error state it never left — with accept / change / reject still offered beside a ranking that
 * was not there. CHG-027 is the fix and these are its cases.
 *
 * **The tests are ordered and the order is load-bearing**, the same way `ATEST-007.spec.ts`
 * documents. One backend, one database and one storm serve the whole run; an identical
 * re-upload resolves to the same scenario (§5, replace in place), so the revision pointer this
 * file advances stays advanced. `fullyParallel: false` keeps tests inside a file in declaration
 * order, which is what makes *a storm at revision 0* reachable at all — and no other spec file
 * loads this fixture, so nothing else can move the pointer underneath it.
 *
 * The fixture is the one ATEST-005 uses at the API level: `SS-ALPHA` and `SS-BRAVO` are
 * identical in every scored factor and differ only in their forecast grid cell, so a swap
 * between them has exactly one possible cause.
 */

const FIXTURE = path.resolve(
  __dirname,
  '../../spec/03-tests/05-executable/fixtures/storm-with-a-forecast-change',
)
const FILES = ['manifest.json', 'assets.csv', 'maintenance.csv', 'weather.csv', 'outages.csv']

const ALPHA = 'SS-ALPHA'
const BRAVO = 'SS-BRAVO'

async function loadedStorm(page: Page) {
  await page.goto('/')
  await page.getByLabel('Email').fill('ops@sgw.example')
  await page.getByLabel('Password').fill('e2e-fixture-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByLabel('Source name').fill('Track shift')
  await page.setInputFiles(
    '#storm-files',
    FILES.map((name) => path.join(FIXTURE, name)),
  )
  await page.getByRole('button', { name: 'Process data' }).click()
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 })
  await page.getByTestId('finish-continue').click()
  await expect(page.getByTestId('forecast-revisions')).toBeVisible()
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

/** The screen never reads as broken. The words RiskList shows when a read failed. */
async function expectTheRankingIsReadable(page: Page) {
  await expect(page.getByTestId('risk-list')).toBeVisible()
  await expect(page.getByText('We could not load the ranking')).toHaveCount(0)
}

test('a freshly loaded storm offers only the revision that has been ranked', async ({ page }) => {
  await loadedStorm(page)

  // Every forecast the file carries is on screen — the operator wants to know the weather
  // moves again — and only the one with an order behind it can be selected.
  await expect(page.getByTestId('view-revision-0')).toBeEnabled()
  await expect(page.getByTestId('view-revision-1')).toBeDisabled()
  await expect(page.getByTestId('view-revision-2')).toBeDisabled()
  await expect(page.getByTestId('revision-not-applied-1')).toContainText(
    'no order to compare',
  )
  await expect(page.getByTestId('forecast-revisions')).toContainText('Forecast revision 0')
  await expect(page.getByTestId('forecast-revisions')).toContainText('2026-08-15T12:00:00Z')

  // The storm is at its first forecast: ALPHA above BRAVO, and nothing is broken.
  await expectTheRankingIsReadable(page)
  const order = await orderOnScreen(page)
  expect(positionOf(order, ALPHA)).toBeLessThan(positionOf(order, BRAVO))
  // Triage is offered because the ranking it decides about is on screen (CHG-060: the
  // whole-ranking decision form left this screen; the per-asset actions are the surface).
  await expect(page.getByTestId('start-triage')).toBeVisible()
})

test('applying the change re-ranks the list, and the previous order is one button away', async ({
  page,
}) => {
  await loadedStorm(page)
  const before = await orderOnScreen(page)
  expect(positionOf(before, ALPHA)).toBeLessThan(positionOf(before, BRAVO))

  await page.getByTestId('apply-forecast').click()

  // The list re-ranked — the first half of AC-005 — and the forecast is the only thing that
  // could have moved these two.
  await expect(page.getByTestId('forecast-revisions')).toContainText('Forecast revision 1')
  await expect(page.getByTestId('view-revision-1')).toBeEnabled()
  await expectTheRankingIsReadable(page)
  const after = await orderOnScreen(page)
  expect(positionOf(after, BRAVO)).toBeLessThan(positionOf(after, ALPHA))

  // The second half, and the one `test-specification.md` names as this test's risk: *"a
  // re-rank destroying the order a decision was made against."*
  // CHG-057: the comparison chips wait behind a disclosure now — open it first.
  await page.getByTestId('forecast-history-toggle').click()
  await page.getByTestId('view-revision-0').click()
  await expect(page.getByTestId('viewing-earlier')).toContainText('It has not changed')
  await expectTheRankingIsReadable(page)
  const recalled = await orderOnScreen(page)
  expect(recalled).toEqual(before)

  // Revision 2 is in the file and has still never been ranked, so it is still not offered.
  await expect(page.getByTestId('view-revision-2')).toBeDisabled()

  // And forward again, so the comparison is a comparison rather than a one-way trip.
  await page.getByTestId('view-revision-1').click()
  await expect(page.getByTestId('viewing-earlier')).toHaveCount(0)
  expect(await orderOnScreen(page)).toEqual(after)
})

test('the storm at its last forecast offers no further change, and says why', async ({
  page,
}) => {
  await loadedStorm(page)

  await page.getByTestId('apply-forecast').click()
  await expect(page.getByTestId('forecast-revisions')).toContainText('Forecast revision 2')

  // A control that stayed live here would offer an action whose only answer is the 409.
  await expect(page.getByTestId('apply-forecast')).toBeDisabled()
  await expect(page.getByTestId('no-further-forecast')).toContainText(
    'no forecast after revision 2',
  )
  // Every revision has an order behind it now, so every one of them can be read back.
  for (const revision of [0, 1, 2]) {
    await expect(page.getByTestId(`view-revision-${revision}`)).toBeEnabled()
  }
  await expect(page.getByTestId('revision-not-applied-2')).toHaveCount(0)
  await expectTheRankingIsReadable(page)
})

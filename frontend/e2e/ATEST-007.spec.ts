import path from 'node:path'

import { expect, Page, test } from '@playwright/test'

/**
 * ATEST-007 — REQ-F-007, AC-007. TASK-005 done criterion 7.
 *
 *     Given  two damage reports for the same location
 *     When   the dispatcher opens the board
 *     Then   both are visible and linked to one repair job, not two
 *
 * **The API-level test of the same id proves the rows; this proves the screen.** TASK-005's
 * seventh done criterion is a claim about what a dispatcher sees — *"two reports at one
 * location render under one job; the empty state reads no damage reported, never all clear"* —
 * and until this file existed it was satisfied by reading `DispatchBoard.tsx` and by nothing
 * executable. Reading source is not evidence that two processes agree.
 *
 * The empty state matters as much as the grouping. `frontend-component-spec.md` fixes the
 * wording because an empty board during a storm is indistinguishable from a network with
 * nothing wrong with it, and this is one of the three screens in this product that look like
 * good news when blank.
 *
 * **The first test must stay first, and the reason is worth writing down.** One backend, one
 * database and one storm serve the whole run: an identical re-upload resolves to the same
 * scenario (`§5`, replace in place) and no endpoint deletes a report, so damage accumulates
 * across tests. `fullyParallel: false` keeps the tests inside a file in declaration order,
 * which is what makes "the board is empty" reachable — and nothing else in the suite files a
 * damage report, so no other file can take it away. Every later test names its **own**
 * neighbourhoods and asserts only against those, so accumulated work cannot make one pass.
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
  // Cleared only after the write succeeded, so an empty field is the acknowledgement.
  await expect(field).toHaveValue('')
}

function jobAt(page: Page, neighbourhood: string) {
  return page.getByTestId('job').filter({ has: page.getByText(neighbourhood, { exact: true }) })
}

test('the empty board reads "no damage reported" and never "all clear"', async ({ page }) => {
  await loadedStorm(page)

  const empty = page.getByTestId('board-empty')
  await expect(empty).toBeVisible()
  await expect(empty).toContainText('No damage reported')
  await expect(empty).toContainText('not a statement that the network is all clear')
  await expect(page.getByTestId('job')).toHaveCount(0)
  // The whole board, not just the empty notice: the words must not appear anywhere on it.
  await expect(page.getByTestId('dispatch-board')).not.toContainText('All clear')
})

test('two reports at one location render as one job with both still visible', async ({
  page,
}) => {
  await loadedStorm(page)

  await fileReport(page, 'Northgate')
  await fileReport(page, 'Northgate')

  // One job for the location — the de-duplication half of AC-007.
  await expect(jobAt(page, 'Northgate')).toHaveCount(1)
  // And neither radio call was thrown away — the half a de-duplicating implementation loses.
  await expect(jobAt(page, 'Northgate').getByTestId('job-report')).toHaveCount(2)
  await expect(jobAt(page, 'Northgate').getByTestId('job-count')).toContainText('2 report(s)')
  await expect(page.getByTestId('board-empty')).toHaveCount(0)
})

test('two different locations render as two jobs', async ({ page }) => {
  await loadedStorm(page)

  await fileReport(page, 'Harbour West')
  await fileReport(page, 'Old Quay')

  // The silent case. Without it, "everything is one job" satisfies the test above perfectly.
  await expect(jobAt(page, 'Harbour West')).toHaveCount(1)
  await expect(jobAt(page, 'Old Quay')).toHaveCount(1)
  await expect(jobAt(page, 'Harbour West').getByTestId('job-report')).toHaveCount(1)
})

test('the same place written differently is still one job on screen', async ({ page }) => {
  await loadedStorm(page)

  await fileReport(page, 'Saltmarsh')
  await fileReport(page, '  saltmarsh ')

  // A capital letter is not a second location, and a second crew is what treating it as one
  // costs. The grouping is the server's; this asserts the screen shows the server's answer
  // rather than a second implementation of the rule.
  await expect(jobAt(page, 'Saltmarsh')).toHaveCount(1)
  await expect(jobAt(page, 'Saltmarsh').getByTestId('job-report')).toHaveCount(2)
})

test('the board says nothing is dispatched and carries no rank or score', async ({ page }) => {
  await loadedStorm(page)

  await fileReport(page, 'Fen End')

  const board = page.getByTestId('dispatch-board')
  await expect(board).toContainText('Adding a report sends nobody anywhere')
  await expect(board).toContainText('never a street or a household')
  const job = jobAt(page, 'Fen End')
  await expect(job).toContainText('pending')
  await expect(job).not.toContainText('High')
  await expect(job).not.toContainText('Medium')
  await expect(job).not.toContainText('Rank')
})
